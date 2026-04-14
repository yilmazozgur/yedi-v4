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

import torch
from torch.utils.data import DataLoader

from .dataset import OBS_DIM, BCDataset, load_parquet, split_by_episode
from .featurizer import NUM_ACTIONS
from .model import BCModelConfig, BCPolicy, bc_cross_entropy, bc_soft_cross_entropy


CHECKPOINT_VERSION: int = 2
"""Bump when the feature layout or model head changes in a breaking way."""


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
        for features, target, _mask, target_set in loader:
            features = features.to(device, non_blocking=True)
            target = target.to(device, non_blocking=True)
            target_set = target_set.to(device, non_blocking=True)
            # Intentionally ignore the dataset's action_mask at train
            # time — see model.py docstring. The mask is still loaded
            # so the dataset format stays stable for future uses.
            logits = model(features, mask=None)
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
    log_fn=print,
) -> dict:
    """Train a BC policy and write ``out_path``. Returns the training summary."""
    torch.manual_seed(seed)
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

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

    if augment_slot_permutation:
        # Train split only — eval metrics must reflect the true (unpermuted)
        # state distribution or we can't compare checkpoints meaningfully.
        train_ds.enable_slot_permutation(seed=seed)
        log_fn("augmentation: slot-permutation on train split (5! = 120 per row)")

    # drop_last=True avoids feeding BatchNorm1d a batch of size 1 on
    # the tail of small datasets — BN in train mode can't compute
    # variance from one sample and raises at runtime. But if the split
    # is smaller than a single batch we'd silently drop everything, so
    # clamp to produce at least two batches and log the chosen size.
    effective_batch = min(batch_size, max(2, len(train_ds) // 2))
    if effective_batch != batch_size:
        log_fn(f"batch_size {batch_size} clamped to {effective_batch} "
               f"(train split has {len(train_ds)} rows)")
    train_loader = DataLoader(train_ds, batch_size=effective_batch, shuffle=True,
                              drop_last=True)
    eval_loader = DataLoader(eval_ds, batch_size=batch_size, shuffle=False)

    cfg = BCModelConfig(hidden_sizes=tuple(hidden_sizes), dropout=dropout)
    model = BCPolicy(cfg).to(dev)
    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    history: list[dict] = []
    best_eval_acc = -1.0
    best_state = None
    started = time.time()

    for epoch in range(1, epochs + 1):
        train_loss, train_acc = _epoch_pass(model, train_loader, dev, optim)
        eval_loss, eval_acc = _epoch_pass(model, eval_loader, dev, None)
        history.append({
            "epoch": epoch,
            "train_loss": train_loss, "train_acc": train_acc,
            "eval_loss":  eval_loss,  "eval_acc":  eval_acc,
        })
        log_fn(f"epoch {epoch:3d}  "
               f"train_loss={train_loss:.4f} acc={train_acc:.3f}  "
               f"eval_loss={eval_loss:.4f} acc={eval_acc:.3f}")
        if eval_acc > best_eval_acc:
            best_eval_acc = eval_acc
            # Detach-and-clone so the checkpoint survives further updates
            # to ``model`` in subsequent epochs.
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    summary = {
        "checkpoint_version": CHECKPOINT_VERSION,
        "obs_dim": OBS_DIM,
        "num_actions": NUM_ACTIONS,
        "best_eval_acc": best_eval_acc,
        "train_seconds": time.time() - started,
        "train_rows": stats.num_train_rows,
        "eval_rows": stats.num_eval_rows,
        "sources": stats.sources,
        "epochs": epochs,
        "history": history,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": best_state if best_state is not None else model.state_dict(),
        "config": cfg.__dict__,
        "summary": summary,
    }, out_path)
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
    )
    # Dump a compact summary next to the checkpoint so ``ls`` tells
    # the story without having to torch.load the .pt.
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
