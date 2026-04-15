"""CLI: train a Decision Transformer on the same Parquet BC dataset uses.

Mirrors ``train_bc.py``: k-fold CV by default, final retrain on all
data for the shipped checkpoint, summary with per-fold accs + mean/std.
The only data-path difference is that rows are re-assembled into
length-``K`` windows by ``DTDataset``.

Example:

    python -m yedi_benchmark.learning.train_dt \\
        --dataset datasets/human_v4.parquet \\
        --out checkpoints/dt_v1.pt \\
        --sources human --epochs 60 --k-folds 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
from torch.utils.data import DataLoader

from .dataset import (
    OBS_DIM,
    BCDataset,
    build_config_vocab,
    kfold_split_by_episode,
    load_parquet,
    split_by_episode,
)
from .dt_dataset import DTDataset, attach_rewards
from .dt_model import (
    DecisionTransformer,
    DTModelConfig,
    dt_accuracy,
    dt_soft_cross_entropy,
)
from .featurizer import NUM_ACTIONS


DT_CHECKPOINT_VERSION: int = 1
"""Bump on any breaking layout change (feature shape, token order,
config embedding semantics). Unlike the BC checkpoint tag, this is
scoped to DT so the two lines of checkpoints can evolve independently."""


def _load_rewards(path: Path | str, sources: set[str] | None) -> np.ndarray:
    """Re-read just the reward column with the same source filter the
    Parquet loader applied. Threading rewards through ``load_parquet``
    would leak a DT-specific payload into the BC path."""
    table = pq.read_table(str(path))
    if sources is not None:
        src_col = table.column("agent_source").to_pylist()
        keep = np.array([s in sources for s in src_col])
        table = table.take(np.nonzero(keep)[0].tolist())
    return table.column("reward").to_numpy(zero_copy_only=False).astype(np.float32)


def _epoch_pass(
    model: DecisionTransformer,
    loader: DataLoader,
    device: torch.device,
    optim: torch.optim.Optimizer | None,
) -> tuple[float, float]:
    training = optim is not None
    model.train(mode=training)
    total_loss = 0.0
    total_correct = 0
    total_n = 0
    grad_ctx = torch.enable_grad() if training else torch.no_grad()
    with grad_ctx:
        for batch in loader:
            states, actions, rtgs, timesteps, attn_mask, equivs, config_id = batch
            states = states.to(device, non_blocking=True)
            actions = actions.to(device, non_blocking=True)
            rtgs = rtgs.to(device, non_blocking=True)
            timesteps = timesteps.to(device, non_blocking=True)
            attn_mask = attn_mask.to(device, non_blocking=True)
            equivs = equivs.to(device, non_blocking=True)
            config_id = config_id.to(device, non_blocking=True)

            logits = model(states, actions, rtgs, timesteps, attn_mask, config_id)
            loss = dt_soft_cross_entropy(logits, equivs, attn_mask)
            if training:
                optim.zero_grad(set_to_none=True)
                loss.backward()
                # Transformer training on small data can spike; clip
                # early rather than discover NaNs in fold 3.
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optim.step()

            n_real = int(attn_mask.sum().item())
            total_loss += loss.item() * n_real
            c, n = dt_accuracy(logits, equivs, attn_mask)
            total_correct += c
            total_n += n
    return total_loss / max(total_n, 1), total_correct / max(total_n, 1)


def _fit_one(
    train_base: BCDataset,
    eval_base: BCDataset | None,
    *,
    rewards_train: np.ndarray,
    rewards_eval: np.ndarray | None,
    cfg: DTModelConfig,
    dev: torch.device,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    seed: int,
    log_fn,
    fold_label: str = "",
) -> tuple[dict, float, list[dict]]:
    torch.manual_seed(seed)

    attach_rewards(train_base, rewards_train)
    train_ds = DTDataset(train_base, context_length=cfg.context_length)
    if eval_base is not None:
        attach_rewards(eval_base, rewards_eval)
        eval_ds = DTDataset(eval_base, context_length=cfg.context_length)
    else:
        eval_ds = None

    effective_batch = min(batch_size, max(2, len(train_ds) // 2))
    if effective_batch != batch_size:
        log_fn(f"{fold_label}batch_size {batch_size} clamped to {effective_batch} "
               f"(train has {len(train_ds)} windows)")
    train_loader = DataLoader(train_ds, batch_size=effective_batch, shuffle=True,
                              drop_last=True)
    eval_loader = (
        DataLoader(eval_ds, batch_size=batch_size, shuffle=False)
        if eval_ds is not None else None
    )

    model = DecisionTransformer(cfg).to(dev)
    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    history: list[dict] = []
    best_eval_acc = -1.0
    best_state: dict | None = None

    for epoch in range(1, epochs + 1):
        train_loss, train_acc = _epoch_pass(model, train_loader, dev, optim)
        if eval_loader is not None:
            eval_loss, eval_acc = _epoch_pass(model, eval_loader, dev, None)
        else:
            eval_loss, eval_acc = float("nan"), float("nan")
        history.append({
            "epoch": epoch,
            "train_loss": train_loss, "train_acc": train_acc,
            "eval_loss":  eval_loss,  "eval_acc":  eval_acc,
        })
        log_fn(f"{fold_label}epoch {epoch:3d}  "
               f"train_loss={train_loss:.4f} acc={train_acc:.3f}  "
               f"eval_loss={eval_loss:.4f} acc={eval_acc:.3f}")
        if eval_loader is not None and eval_acc > best_eval_acc:
            best_eval_acc = eval_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        best_eval_acc = float("nan")
    return best_state, best_eval_acc, history


def train(
    dataset: BCDataset,
    *,
    rewards: np.ndarray,
    out_path: Path,
    context_length: int = 20,
    d_model: int = 128,
    n_heads: int = 4,
    n_layers: int = 2,
    dropout: float = 0.2,
    config_emb_dim: int = 8,
    eval_fraction: float = 0.2,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    seed: int = 42,
    device: str | None = None,
    k_folds: int = 5,
    log_fn=print,
) -> dict:
    """Train a DT policy and write ``out_path``. Returns the summary.

    ``dataset`` is a ``BCDataset`` loaded via ``load_parquet``; ``rewards``
    is the row-aligned reward column (see ``_load_rewards``). We keep the
    two separate so the BC path — which doesn't use rewards — stays
    unchanged.
    """
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    config_vocab = build_config_vocab(dataset)
    dataset.set_config_vocab(config_vocab)
    log_fn(f"config vocab: {len(config_vocab)} distinct config_key(s) "
           f"(+ UNK slot at id 0)")

    cfg = DTModelConfig(
        context_length=context_length,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        dropout=dropout,
        config_vocab_size=len(config_vocab) + 1 if config_emb_dim > 0 else 0,
        config_emb_dim=config_emb_dim,
    )
    started = time.time()

    def _rewards_for(base: BCDataset) -> np.ndarray:
        # Align rewards by (episode_id, row order) using the parent row
        # indices. We rebuild from the parent dataset's episode_ids —
        # k-fold produces splits that preserve the original row order,
        # so per-split reward slices come from matching masks.
        # Caller provides the full rewards array; we expect _row_indices
        # set by split helpers, which isn't available, so we match by
        # (episode_id, step-order) via a straightforward mask lookup.
        raise RuntimeError("internal: _rewards_for should be bypassed — "
                           "we split rewards alongside the features below.")

    if k_folds <= 1:
        # Single-split path: replicate the mask used by split_by_episode
        # so rewards line up with the returned BCDataset rows.
        train_base, eval_base, stats = split_by_episode(
            dataset, eval_fraction=eval_fraction, seed=seed,
        )
        log_fn(f"split: train={stats.num_train_rows} rows / "
               f"{stats.num_train_episodes} eps, eval={stats.num_eval_rows} "
               f"rows / {stats.num_eval_episodes} eps, sources={stats.sources}")
        if len(train_base) == 0 or len(eval_base) == 0:
            raise ValueError(
                f"empty split — need ≥2 episodes (got "
                f"train={stats.num_train_episodes}, eval={stats.num_eval_episodes})"
            )
        train_mask = np.isin(dataset.episode_ids, train_base.episode_ids)
        eval_mask = np.isin(dataset.episode_ids, eval_base.episode_ids)
        final_state, best_eval_acc, history = _fit_one(
            train_base, eval_base,
            rewards_train=rewards[train_mask],
            rewards_eval=rewards[eval_mask],
            cfg=cfg, dev=dev, epochs=epochs, batch_size=batch_size,
            lr=lr, weight_decay=weight_decay, seed=seed, log_fn=log_fn,
        )
        fold_eval_accs = [best_eval_acc]
        mean_eval_acc = best_eval_acc
        std_eval_acc = 0.0
        train_rows = stats.num_train_rows
        eval_rows = stats.num_eval_rows
        sources = stats.sources
        cv_histories: list[list[dict]] = []
    else:
        unique_eps = len({str(e) for e in dataset.episode_ids})
        if unique_eps < 2:
            raise ValueError(f"empty split — need ≥2 episodes (got {unique_eps})")
        effective_k = min(k_folds, unique_eps)
        if effective_k < k_folds:
            log_fn(f"k_folds={k_folds} > num_episodes={unique_eps}, "
                   f"falling back to leave-one-out (k={effective_k})")

        folds = kfold_split_by_episode(dataset, k=effective_k, seed=seed)
        fold_eval_accs = []
        cv_histories = []
        for i, (tr, ev, stats) in enumerate(folds, 1):
            label = f"[fold {i}/{effective_k}] "
            log_fn(f"{label}train={stats.num_train_rows} rows / "
                   f"{stats.num_train_episodes} eps, eval={stats.num_eval_rows} "
                   f"rows / {stats.num_eval_episodes} eps")
            tr_mask = np.isin(dataset.episode_ids, tr.episode_ids)
            ev_mask = np.isin(dataset.episode_ids, ev.episode_ids)
            _, acc, hist = _fit_one(
                tr, ev,
                rewards_train=rewards[tr_mask],
                rewards_eval=rewards[ev_mask],
                cfg=cfg, dev=dev, epochs=epochs, batch_size=batch_size,
                lr=lr, weight_decay=weight_decay, seed=seed, log_fn=log_fn,
                fold_label=label,
            )
            fold_eval_accs.append(acc)
            cv_histories.append(hist)

        mean_eval_acc = float(np.mean(fold_eval_accs))
        std_eval_acc = float(np.std(fold_eval_accs))
        log_fn(f"k-fold CV: eval_acc = {mean_eval_acc:.3f} ± {std_eval_acc:.3f} "
               f"across {effective_k} folds "
               f"(per-fold: {[f'{a:.3f}' for a in fold_eval_accs]})")

        log_fn(f"[final] retraining on all {len(dataset)} rows for shipped checkpoint")
        final_state, _, history = _fit_one(
            dataset, None,
            rewards_train=rewards, rewards_eval=None,
            cfg=cfg, dev=dev, epochs=epochs, batch_size=batch_size,
            lr=lr, weight_decay=weight_decay, seed=seed, log_fn=log_fn,
            fold_label="[final] ",
        )
        best_eval_acc = max(fold_eval_accs)
        train_rows = len(dataset)
        eval_rows = 0
        sources = {}
        for s in dataset.sources:
            sources[str(s)] = sources.get(str(s), 0) + 1

    summary = {
        "checkpoint_version": DT_CHECKPOINT_VERSION,
        "model_kind": "decision_transformer",
        "obs_dim": OBS_DIM,
        "num_actions": NUM_ACTIONS,
        "context_length": context_length,
        "best_eval_acc": best_eval_acc,
        "mean_eval_acc": mean_eval_acc,
        "std_eval_acc": std_eval_acc,
        "fold_eval_accs": fold_eval_accs,
        "k_folds": k_folds,
        "train_seconds": time.time() - started,
        "train_rows": train_rows,
        "eval_rows": eval_rows,
        "sources": sources,
        "epochs": epochs,
        "history": history,
        "cv_histories": cv_histories,
        "config_vocab": config_vocab,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": final_state,
        "config": cfg.__dict__,
        "config_vocab": config_vocab,
        "summary": summary,
    }, out_path)
    if k_folds > 1:
        log_fn(f"wrote {out_path} (CV eval_acc={mean_eval_acc:.3f}±{std_eval_acc:.3f})")
    else:
        log_fn(f"wrote {out_path} (best eval_acc={best_eval_acc:.3f})")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--sources", nargs="*",
                   choices=["human", "greedy", "random", "llm", "unknown"])
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--eval-fraction", type=float, default=0.2)
    p.add_argument("--context-length", type=int, default=20)
    p.add_argument("--d-model", type=int, default=128)
    p.add_argument("--n-heads", type=int, default=4)
    p.add_argument("--n-layers", type=int, default=2)
    p.add_argument("--dropout", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default=None)
    p.add_argument("--k-folds", type=int, default=5)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    sources = set(args.sources) if args.sources else None
    ds = load_parquet(args.dataset, sources=sources)
    rewards = _load_rewards(args.dataset, sources)
    print(f"loaded {len(ds)} rows from {args.dataset}")
    summary = train(
        ds,
        rewards=rewards,
        out_path=args.out,
        context_length=args.context_length,
        d_model=args.d_model,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        dropout=args.dropout,
        eval_fraction=args.eval_fraction,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        seed=args.seed,
        device=args.device,
        k_folds=args.k_folds,
    )
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
