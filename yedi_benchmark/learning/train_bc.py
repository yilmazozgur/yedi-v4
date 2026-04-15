"""CLI: train a BC policy on an exported Parquet dataset.

Example:

    python -m yedi_benchmark.learning.train_bc \\
        --dataset datasets/yedi_bc.parquet \\
        --out checkpoints/bc_v1.pt \\
        --sources human greedy \\
        --epochs 20

The checkpoint is self-describing: it carries the featurizer version,
observation dimension, and training summary so ``BehaviorCloningAgent``
can sanity-check at load time.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .dataset import (
    OBS_DIM,
    UNK_CONFIG_ID,
    BCDataset,
    build_config_vocab,
    kfold_split_by_episode,
    load_parquet,
    split_by_episode,
)
from .featurizer import NUM_ACTIONS
from .model import BCModelConfig, BCPolicy, bc_cross_entropy, bc_soft_cross_entropy


CHECKPOINT_VERSION: int = 3
"""Bump when the feature layout or model head changes in a breaking way.

v3 adds the sub-mode multi-hot to the flat feature vector and a learned
config_key embedding as a second input to the model."""


def _epoch_pass(
    model: BCPolicy,
    loader: DataLoader,
    device: torch.device,
    optim: torch.optim.Optimizer | None,
) -> tuple[float, float]:
    """One full pass. ``optim=None`` runs in eval mode (no grad, no step).

    Returns (mean_loss, top1_accuracy)."""
    training = optim is not None
    model.train(mode=training)
    total_loss = 0.0
    total_correct = 0
    total_n = 0
    grad_ctx = torch.enable_grad() if training else torch.no_grad()
    with grad_ctx:
        for features, target, _mask, target_set, config_id in loader:
            features = features.to(device, non_blocking=True)
            target = target.to(device, non_blocking=True)
            target_set = target_set.to(device, non_blocking=True)
            config_id = config_id.to(device, non_blocking=True)
            # Intentionally ignore the dataset's action_mask at train
            # time — see model.py docstring. The mask is still loaded
            # so the dataset format stays stable for future uses.
            logits = model(features, mask=None, config_id=config_id)
            # Soft CE over the equivalence class (e.g. "park card in
            # any empty slot"). Reduces to plain CE when the set is a
            # singleton, so DRAW/SELL/merge targets are unaffected.
            loss = bc_soft_cross_entropy(logits, target_set)
            if training:
                optim.zero_grad(set_to_none=True)
                loss.backward()
                optim.step()
            total_loss += loss.item() * features.size(0)
            # Accuracy credits any action in the equivalence class as
            # correct — matches what the loss is actually optimizing.
            preds = logits.argmax(dim=1)
            correct = target_set[torch.arange(preds.size(0), device=preds.device), preds]
            total_correct += int(correct.sum())
            total_n += features.size(0)
    return total_loss / max(total_n, 1), total_correct / max(total_n, 1)


def _fit_one(
    train_ds: BCDataset,
    eval_ds: BCDataset | None,
    *,
    cfg: BCModelConfig,
    dev: torch.device,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    augment_slot_permutation: bool,
    seed: int,
    log_fn,
    fold_label: str = "",
) -> tuple[dict, float, list[dict]]:
    """Train one BCPolicy on ``train_ds`` (+ optional eval_ds).

    Returns (best_state_dict, best_eval_acc, history). When ``eval_ds`` is
    None there's no validation — we return the final epoch's state and
    ``best_eval_acc=float('nan')`` (used for the post-CV full-data retrain).
    """
    torch.manual_seed(seed)

    if augment_slot_permutation:
        train_ds.enable_slot_permutation(seed=seed)

    effective_batch = min(batch_size, max(2, len(train_ds) // 2))
    if effective_batch != batch_size:
        log_fn(f"{fold_label}batch_size {batch_size} clamped to {effective_batch} "
               f"(train split has {len(train_ds)} rows)")
    train_loader = DataLoader(train_ds, batch_size=effective_batch, shuffle=True,
                              drop_last=True)
    eval_loader = (
        DataLoader(eval_ds, batch_size=batch_size, shuffle=False)
        if eval_ds is not None else None
    )

    model = BCPolicy(cfg).to(dev)
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
        # No eval — final state is what we ship.
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        best_eval_acc = float("nan")
    return best_state, best_eval_acc, history


def train(
    dataset: BCDataset,
    *,
    out_path: Path,
    eval_fraction: float = 0.2,
    epochs: int = 20,
    batch_size: int = 256,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    hidden_sizes: tuple[int, ...] = (256, 256),
    dropout: float = 0.1,
    seed: int = 42,
    device: str | None = None,
    augment_slot_permutation: bool = True,
    config_emb_dim: int = 8,
    k_folds: int = 5,
    log_fn=print,
) -> dict:
    """Train a BC policy and write ``out_path``. Returns the training summary.

    K-fold CV is the default. The human dataset has tens of episodes, so a
    single eval split of a handful of episodes has enough variance to hide
    real improvements or falsely credit them — we average across ``k_folds``
    folds and report mean ± std. After CV we retrain on the full dataset
    for the same epoch budget and save *that* as the shipped checkpoint
    (CV measured the metric; the model should see every row).

    Pass ``k_folds=1`` to run a single train/eval split (useful for
    debugging or datasets too small to fold).
    """
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    config_vocab = build_config_vocab(dataset)
    dataset.set_config_vocab(config_vocab)
    log_fn(f"config vocab: {len(config_vocab)} distinct config_key(s) "
           f"(+ UNK slot at id 0)")

    cfg = BCModelConfig(
        hidden_sizes=tuple(hidden_sizes),
        dropout=dropout,
        config_vocab_size=len(config_vocab) + 1 if config_emb_dim > 0 else 0,
        config_emb_dim=config_emb_dim,
    )

    started = time.time()
    fit_kwargs = dict(
        cfg=cfg, dev=dev, epochs=epochs, batch_size=batch_size, lr=lr,
        weight_decay=weight_decay,
        augment_slot_permutation=augment_slot_permutation,
        seed=seed, log_fn=log_fn,
    )

    if k_folds <= 1:
        # Escape hatch: single train/eval split (old behavior).
        train_ds, eval_ds, stats = split_by_episode(
            dataset, eval_fraction=eval_fraction, seed=seed,
        )
        log_fn(
            f"split: train={stats.num_train_rows} rows / {stats.num_train_episodes} eps, "
            f"eval={stats.num_eval_rows} rows / {stats.num_eval_episodes} eps, "
            f"sources={stats.sources}"
        )
        if len(train_ds) == 0 or len(eval_ds) == 0:
            raise ValueError(
                f"empty split — need ≥2 episodes (got train={stats.num_train_episodes}, "
                f"eval={stats.num_eval_episodes})"
            )
        final_state, best_eval_acc, history = _fit_one(train_ds, eval_ds, **fit_kwargs)
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
            raise ValueError(
                f"empty split — need ≥2 episodes (got {unique_eps})"
            )
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
            _, acc, hist = _fit_one(tr, ev, fold_label=label, **fit_kwargs)
            fold_eval_accs.append(acc)
            cv_histories.append(hist)

        mean_eval_acc = float(np.mean(fold_eval_accs))
        std_eval_acc = float(np.std(fold_eval_accs))
        log_fn(f"k-fold CV: eval_acc = {mean_eval_acc:.3f} ± {std_eval_acc:.3f} "
               f"across {effective_k} folds "
               f"(per-fold: {[f'{a:.3f}' for a in fold_eval_accs]})")

        # Shipped checkpoint: retrain on all data (no held-out eval).
        log_fn(f"[final] retraining on all {len(dataset)} rows for shipped checkpoint")
        final_state, _, history = _fit_one(
            dataset, None, fold_label="[final] ", **fit_kwargs,
        )
        best_eval_acc = max(fold_eval_accs)
        train_rows = len(dataset)
        eval_rows = 0
        sources = {}
        for s in dataset.sources:
            sources[str(s)] = sources.get(str(s), 0) + 1

    summary = {
        "checkpoint_version": CHECKPOINT_VERSION,
        "obs_dim": OBS_DIM,
        "num_actions": NUM_ACTIONS,
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
        log_fn(f"wrote {out_path} "
               f"(CV eval_acc={mean_eval_acc:.3f}±{std_eval_acc:.3f})")
    else:
        log_fn(f"wrote {out_path} (best eval_acc={best_eval_acc:.3f})")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True,
                   help="Parquet file from export_dataset")
    p.add_argument("--out", type=Path, required=True,
                   help="Checkpoint path (.pt)")
    p.add_argument("--sources", nargs="*",
                   choices=["human", "greedy", "random", "llm", "unknown"],
                   help="Only train on these agent sources (default: all)")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--eval-fraction", type=float, default=0.2)
    p.add_argument("--hidden-sizes", type=int, nargs="*", default=[256, 256])
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default=None,
                   help="cuda|cpu (default: auto)")
    p.add_argument("--no-augment", dest="augment", action="store_false",
                   help="Disable slot-permutation augmentation on train split")
    p.set_defaults(augment=True)
    p.add_argument("--k-folds", type=int, default=5,
                   help="K-fold CV folds (default 5; pass 1 for single split)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    ds = load_parquet(args.dataset,
                      sources=set(args.sources) if args.sources else None)
    print(f"loaded {len(ds)} rows from {args.dataset}")
    summary = train(
        ds,
        out_path=args.out,
        eval_fraction=args.eval_fraction,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        hidden_sizes=tuple(args.hidden_sizes),
        dropout=args.dropout,
        seed=args.seed,
        device=args.device,
        augment_slot_permutation=args.augment,
        k_folds=args.k_folds,
    )
    # Dump a compact summary next to the checkpoint so ``ls`` tells
    # the story without having to torch.load the .pt.
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
