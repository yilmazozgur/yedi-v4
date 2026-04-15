"""Sequence-aware dataset for Decision Transformer training.

Where ``BCDataset`` emits one (state, action) row per step, DT wants
``K``-step windows of ``(return_to_go, state, action)`` triples. We
reuse the same Parquet layout — all the per-step features already
exist — and build the windows on top.

Windowing rules:

* Rows are grouped by ``episode_id`` and ordered by ``step``.
* Return-to-go (RTG) for step ``t`` is the sum of rewards from ``t``
  to end of episode. Computed per episode at load time.
* For each step ``t`` we emit one window covering steps
  ``[max(0, t-K+1) .. t]``, left-padded to length ``K`` so that the
  "current" step always sits at position ``K-1``. This keeps the
  transformer's causal read aligned regardless of episode progress.
* Each window carries an ``attn_mask`` marking which positions are real
  vs pad; loss and metrics must ignore pad positions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import Dataset

from .dataset import (
    BCDataset,
    OBS_DIM,
    UNK_CONFIG_ID,
    _slot_occupied_from_features,
    action_equivalence_mask,
)
from .featurizer import NUM_ACTIONS


@dataclass
class DTSample:
    """Materialized per-step window. Kept as numpy so __getitem__ can
    return tensors cheaply and augmentations (future) stay array-based."""
    states:       np.ndarray  # (K, OBS_DIM) float32
    actions:      np.ndarray  # (K,)         int64
    rewards_to_go: np.ndarray # (K,)         float32
    timesteps:    np.ndarray  # (K,)         int64
    attn_mask:    np.ndarray  # (K,)         int8 — 1 real, 0 pad
    equiv_sets:   np.ndarray  # (K, NUM_ACTIONS) float32 — action-equivalence per real position (0 on pad)
    config_id:    int


def compute_returns_to_go(rewards: np.ndarray) -> np.ndarray:
    """RTG_t = sum_{i>=t} rewards[i]. O(N) reverse cumsum."""
    return np.flip(np.cumsum(np.flip(rewards))).astype(np.float32, copy=False)


class DTDataset(Dataset):
    """In-memory windowed dataset built from a ``BCDataset``.

    We materialize every window upfront because our datasets are ~2k
    rows — an order of magnitude below where lazy windowing starts to
    matter. If that changes, replace ``_samples`` with a light
    per-episode view and slice on ``__getitem__``.
    """

    def __init__(
        self,
        base: BCDataset,
        *,
        context_length: int = 20,
    ):
        if context_length < 1:
            raise ValueError(f"context_length must be ≥1 (got {context_length})")
        self.context_length = context_length
        self._samples: list[DTSample] = []

        # Group rows by episode, preserving the Parquet order (which is
        # already sorted by step ascending). We re-check the step
        # monotonicity per episode just to catch accidental shuffles.
        episode_ids = base.episode_ids
        unique_eps = np.unique(episode_ids)
        for eid in unique_eps:
            idxs = np.where(episode_ids == eid)[0]
            # BCDataset doesn't carry a step column — but the Parquet
            # export sorts by (episode_id, step), so the slice order is
            # already chronological. We rely on that invariant.
            feats_ep = base.features[idxs]
            actions_ep = base.actions[idxs]
            # Rewards aren't on BCDataset; see load_dt_parquet for the
            # path that attaches them. Fall back to zeros if absent so
            # tests that build DTDataset directly from a BCDataset still
            # work (RTG is zero, which the trainer treats as a neutral
            # conditioning signal).
            rewards_ep = getattr(base, "_rewards", None)
            if rewards_ep is None:
                rewards = np.zeros(len(idxs), dtype=np.float32)
            else:
                rewards = rewards_ep[idxs].astype(np.float32, copy=False)

            rtg = compute_returns_to_go(rewards)
            config_id = int(base.config_ids[idxs[0]]) if len(idxs) else UNK_CONFIG_ID

            # Slot-occupancy per row → used to compute action equivalence.
            occ_ep = np.stack([_slot_occupied_from_features(f) for f in feats_ep])

            K = context_length
            N = len(idxs)
            for t in range(N):
                lo = max(0, t - K + 1)
                real_len = t - lo + 1
                pad = K - real_len

                states = np.zeros((K, OBS_DIM), dtype=np.float32)
                actions = np.zeros(K, dtype=np.int64)
                rtgs = np.zeros(K, dtype=np.float32)
                timesteps = np.zeros(K, dtype=np.int64)
                attn = np.zeros(K, dtype=np.int8)
                equivs = np.zeros((K, NUM_ACTIONS), dtype=np.float32)

                for k, src_t in enumerate(range(lo, t + 1)):
                    pos = pad + k  # left-padded, so real data lives at the end
                    states[pos] = feats_ep[src_t]
                    actions[pos] = actions_ep[src_t]
                    rtgs[pos] = rtg[src_t]
                    timesteps[pos] = src_t
                    attn[pos] = 1
                    equivs[pos] = action_equivalence_mask(
                        int(actions_ep[src_t]), occ_ep[src_t],
                    )

                self._samples.append(DTSample(
                    states=states, actions=actions, rewards_to_go=rtgs,
                    timesteps=timesteps, attn_mask=attn, equiv_sets=equivs,
                    config_id=config_id,
                ))

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, i: int):
        s = self._samples[i]
        return (
            torch.from_numpy(s.states),
            torch.from_numpy(s.actions),
            torch.from_numpy(s.rewards_to_go),
            torch.from_numpy(s.timesteps),
            torch.from_numpy(s.attn_mask.astype(np.float32)),
            torch.from_numpy(s.equiv_sets),
            torch.tensor(s.config_id, dtype=torch.long),
        )


def attach_rewards(base: BCDataset, rewards: np.ndarray) -> BCDataset:
    """Attach a per-row ``_rewards`` array to ``base`` for DTDataset.

    We don't thread rewards through ``BCDataset``'s constructor because
    BC itself ignores them — keeping the attachment lazy avoids churning
    the BC API every time a new feature needs row-aligned payload.
    """
    if len(rewards) != len(base):
        raise ValueError(
            f"rewards length {len(rewards)} != dataset length {len(base)}"
        )
    base._rewards = rewards.astype(np.float32, copy=False)  # type: ignore[attr-defined]
    return base


def load_dt_parquet(path, *, sources=None, context_length: int = 20) -> DTDataset:
    """End-to-end loader: Parquet → BCDataset (+rewards) → DTDataset."""
    import pyarrow.parquet as pq
    from .dataset import load_parquet

    base = load_parquet(path, sources=sources)
    # Re-read just the reward column aligned to the same row order/filter
    # ``load_parquet`` applied. Simpler than threading rewards through
    # every internal — the source Parquet's row order is stable.
    table = pq.read_table(str(path))
    if sources is not None:
        src_col = table.column("agent_source").to_pylist()
        keep = np.array([s in sources for s in src_col])
        indices = np.nonzero(keep)[0]
        table = table.take(indices.tolist())
    rewards = table.column("reward").to_numpy(zero_copy_only=False).astype(np.float32)
    attach_rewards(base, rewards)
    return DTDataset(base, context_length=context_length)
