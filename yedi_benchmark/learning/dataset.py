"""PyTorch dataset over a featurized Parquet file.

The Parquet written by ``export_dataset`` has one row per step. For BC
we flatten every feature into a single ``(OBS_DIM,)`` vector and return
it alongside the expert action and the action mask.

Episode-level splitting
-----------------------
We must not leak step K of episode E into the eval set while step K+1
stays in train — the states are near-duplicates and the model would
trivially memorize them. Splits are therefore done at the *episode* level:
an entire episode lives in exactly one split.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pyarrow.parquet as pq
import torch
from torch.utils.data import Dataset

from .featurizer import (
    DIMENSIONS_DIM,
    NUM_ACTIONS,
    NUM_SLOTS,
    OBS_SCALAR_FIELDS,
    SLOT_FEATURE_DIM,
    SUB_MODES_DIM,
    WORD_HASH_DIM,
)


OBS_DIM: int = (
    len(OBS_SCALAR_FIELDS)
    + NUM_SLOTS * SLOT_FEATURE_DIM
    + NUM_SLOTS * WORD_HASH_DIM
    + DIMENSIONS_DIM
    + SUB_MODES_DIM
)
"""Flat feature-vector width: 4 scalars + 77 slot + 448 word + 7 dims + 7 subs = 543.

Layout order must match ``agents.bc_agent._featurize_live`` — any reorder
is a breaking change that the checkpoint version guard must catch."""

UNK_CONFIG_ID: int = 0
"""Config-id reserved for 'unknown at training time'. The BC agent falls
back to this when a checkpoint is asked to play a config it never saw."""


_SLOT_BLOCK_OFFSET: int = len(OBS_SCALAR_FIELDS)
_WORD_BLOCK_OFFSET: int = _SLOT_BLOCK_OFFSET + NUM_SLOTS * SLOT_FEATURE_DIM
_OCCUPIED_FEATURE_INDEX: int = 0  # slot feature layout: [occupied, ...]


def _slot_occupied_from_features(feat: np.ndarray) -> np.ndarray:
    """Extract the per-slot occupancy bits (slots 0..5) from a flat feature row.

    Mirrors the layout in ``load_parquet`` and ``_featurize_live``: the
    slot block starts right after the scalar fields and stores NUM_SLOTS
    × SLOT_FEATURE_DIM values in row-major order, with ``occupied`` as
    feature index 0 within each slot. Slots 0..5 cover the 'new' slot and
    the 5 board slots — the only ones the action space can address.
    """
    offsets = _SLOT_BLOCK_OFFSET + np.arange(6) * SLOT_FEATURE_DIM + _OCCUPIED_FEATURE_INDEX
    return (feat[offsets] > 0.5).astype(np.float32)


def action_equivalence_mask(action: int, slot_occupied: np.ndarray) -> np.ndarray:
    """Multi-hot (NUM_ACTIONS,) mask of actions semantically equivalent to ``action``.

    Rules:
      * DRAW (0) and SELL (31-36) are unique — slot choice is not arbitrary.
      * MOVE to an occupied dst is a merge — unique per src/dst pair.
      * MOVE(src, empty_dst) is equivalent to MOVE(src, any_other_empty_dst):
        the player's choice of which empty board slot to park a card in is
        arbitrary label noise, and the resulting state is identical.

    ``slot_occupied`` is a length-6 array over slot indices 0..5 (new + 5
    board slots), 1.0 if currently holding a card.
    """
    mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
    mask[action] = 1.0
    if 1 <= action <= 30:
        src_idx = (action - 1) // 5
        dst_idx = (action - 1) % 5 + 1
        if slot_occupied[dst_idx] < 0.5:  # move, not merge
            for d in range(1, 6):
                if slot_occupied[d] < 0.5:
                    mask[1 + src_idx * 5 + (d - 1)] = 1.0
    return mask


def _build_action_perm(old_to_new: np.ndarray) -> np.ndarray:
    """Length-NUM_ACTIONS array mapping old action id -> new action id.

    ``old_to_new`` is indexed by old slot id (0..5) and holds the new slot
    id after the board permutation. By convention ``old_to_new[0] == 0``
    because slot 0 ('new') is always fixed — only slots 1..5 shuffle.
    """
    act_perm = np.empty(NUM_ACTIONS, dtype=np.int64)
    act_perm[0] = 0  # DRAW
    for a in range(1, 31):
        src = (a - 1) // 5
        dst = (a - 1) % 5 + 1
        act_perm[a] = 1 + int(old_to_new[src]) * 5 + (int(old_to_new[dst]) - 1)
    for a in range(31, 37):
        src = a - 31
        act_perm[a] = 31 + int(old_to_new[src])
    return act_perm


def _apply_slot_permutation(
    feat: np.ndarray,
    action: int,
    mask: np.ndarray,
    equiv: np.ndarray,
    new_to_old: np.ndarray,
) -> tuple[np.ndarray, int, np.ndarray, np.ndarray]:
    """Relabel board slots 1..5 in a feature row and remap action indices.

    The five addressable board slots have no intrinsic identity — the
    player only cares about the cards they hold, not which column they
    sit in. This lets us turn one demonstration into up to 5! = 120
    synthetic rows by shuffling {1..5} and carrying the action, mask and
    equivalence-class mask through the same permutation.

    ``new_to_old[i]`` is the old slot id that now sits at new position
    ``i + 1``. Slot 0 ('new') and slot 6 (not action-addressable) are
    never permuted.
    """
    old_to_new = np.zeros(6, dtype=np.int64)
    for new_pos, old_slot in enumerate(new_to_old, start=1):
        old_to_new[int(old_slot)] = new_pos

    new_feat = feat.copy()
    for new_slot in range(1, 6):
        old_slot = int(new_to_old[new_slot - 1])
        s_lo = _SLOT_BLOCK_OFFSET + new_slot * SLOT_FEATURE_DIM
        o_lo = _SLOT_BLOCK_OFFSET + old_slot * SLOT_FEATURE_DIM
        new_feat[s_lo:s_lo + SLOT_FEATURE_DIM] = feat[o_lo:o_lo + SLOT_FEATURE_DIM]
        w_lo = _WORD_BLOCK_OFFSET + new_slot * WORD_HASH_DIM
        wo_lo = _WORD_BLOCK_OFFSET + old_slot * WORD_HASH_DIM
        new_feat[w_lo:w_lo + WORD_HASH_DIM] = feat[wo_lo:wo_lo + WORD_HASH_DIM]

    act_perm = _build_action_perm(old_to_new)
    new_action = int(act_perm[action])
    new_mask = np.zeros_like(mask)
    new_mask[act_perm] = mask
    new_equiv = np.zeros_like(equiv)
    new_equiv[act_perm] = equiv
    return new_feat, new_action, new_mask, new_equiv


@dataclass
class SplitStats:
    """Summary of a train/eval split — used by the trainer CLI to print
    a human-readable sanity line before kicking off training."""
    num_train_rows: int
    num_eval_rows: int
    num_train_episodes: int
    num_eval_episodes: int
    sources: dict[str, int]


class BCDataset(Dataset):
    """In-memory dataset. The real data is ~10-100k rows so loading it
    all at once is simpler than a streaming reader; revisit if we ever
    hit millions of rows."""

    def __init__(
        self,
        features: np.ndarray,      # (N, OBS_DIM) float32
        actions:  np.ndarray,      # (N,)         int64
        masks:    np.ndarray,      # (N, 37)      int8
        episode_ids: np.ndarray,   # (N,)         object
        sources:  np.ndarray,      # (N,)         object
        config_keys: np.ndarray | None = None,   # (N,) object, per-row config_key
    ):
        assert features.shape[1] == OBS_DIM
        assert masks.shape[1] == NUM_ACTIONS
        self.features = features
        self.actions = actions
        self.masks = masks
        self.episode_ids = episode_ids
        self.sources = sources
        self.config_keys = (
            config_keys if config_keys is not None
            else np.array([""] * len(actions), dtype=object)
        )
        self.augment_slot_permutation: bool = False
        self._aug_rng: np.random.Generator | None = None
        # Populated by ``set_config_vocab`` — until then ``config_ids`` is
        # all-UNK, which lets the trainer inspect rows before binding a
        # vocab and lets tests skip the embedding entirely.
        self.config_ids: np.ndarray = np.full(len(actions), UNK_CONFIG_ID, dtype=np.int64)

    def set_config_vocab(self, vocab: dict[str, int]) -> None:
        """Bind a ``config_key -> id`` map, materialising ``config_ids``.

        Keys not in ``vocab`` resolve to ``UNK_CONFIG_ID`` so an eval split
        or a live session on an unseen config still produces a valid id.
        """
        self.config_ids = np.array(
            [vocab.get(str(k), UNK_CONFIG_ID) for k in self.config_keys],
            dtype=np.int64,
        )

    def enable_slot_permutation(self, seed: int = 0) -> None:
        """Turn on random slot-permutation augmentation for this split.

        Call on the train split only — the eval split must stay
        unpermuted so metrics reflect true state distributions.
        """
        self.augment_slot_permutation = True
        self._aug_rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.actions)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        feat = self.features[i].astype(np.float32, copy=False)
        action = int(self.actions[i])
        mask = self.masks[i].astype(np.float32)
        equiv = action_equivalence_mask(action, _slot_occupied_from_features(feat))
        if self.augment_slot_permutation and self._aug_rng is not None:
            new_to_old = self._aug_rng.permutation(5) + 1
            feat, action, mask, equiv = _apply_slot_permutation(
                feat, action, mask, equiv, new_to_old,
            )
        return (
            torch.from_numpy(np.ascontiguousarray(feat)),
            torch.tensor(action, dtype=torch.long),
            torch.from_numpy(np.ascontiguousarray(mask)),
            torch.from_numpy(np.ascontiguousarray(equiv)),
            torch.tensor(int(self.config_ids[i]), dtype=torch.long),
        )


def _unpack_fixed_list(col, expected_dim: int) -> np.ndarray:
    """Flatten a pyarrow fixed_size_list column into a 2-D ndarray.

    ``to_numpy(zero_copy_only=False)`` yields an ndarray of Python lists
    for list columns, not a proper 2-D block — we need the latter for
    torch.from_numpy to work without a per-row copy.
    """
    values = col.combine_chunks().values.to_numpy(zero_copy_only=False)
    return values.reshape(-1, expected_dim)


def load_parquet(
    path: Path | str,
    *,
    sources: Iterable[str] | None = None,
) -> BCDataset:
    """Load a featurized Parquet into a ``BCDataset``.

    ``sources`` optionally filters rows by ``agent_source`` (e.g. train
    on human-only). Row order follows the Parquet file, which follows
    ``export_dataset``'s sort (episode_id ascending, step ascending).
    """
    table = pq.read_table(str(path))
    if sources is not None:
        source_col = table.column("agent_source").to_pylist()
        mask = np.array([s in sources for s in source_col])
        if not mask.any():
            raise ValueError(f"No rows match sources={sources!r}")
        indices = np.nonzero(mask)[0]
        table = table.take(indices.tolist())

    scalars = np.stack([
        table.column(name).to_numpy(zero_copy_only=False).astype(np.float32)
        for name in OBS_SCALAR_FIELDS
    ], axis=1)
    slots     = _unpack_fixed_list(table.column("slots"),
                                   NUM_SLOTS * SLOT_FEATURE_DIM).astype(np.float32)
    word_hash = _unpack_fixed_list(table.column("word_hash"),
                                   NUM_SLOTS * WORD_HASH_DIM).astype(np.float32)
    dims_active = _unpack_fixed_list(table.column("dims_active"),
                                     DIMENSIONS_DIM).astype(np.float32)
    # Backfill for older parquets that predate the sub_modes_active column
    # — zero-filling keeps OBS_DIM consistent without crashing on legacy
    # files. New trainers exporting fresh data will always write the column.
    if "sub_modes_active" in table.column_names:
        sub_modes = _unpack_fixed_list(table.column("sub_modes_active"),
                                       SUB_MODES_DIM).astype(np.float32)
    else:
        sub_modes = np.zeros((len(table), SUB_MODES_DIM), dtype=np.float32)
    masks     = _unpack_fixed_list(table.column("action_mask"),
                                   NUM_ACTIONS).astype(np.int8)
    actions   = table.column("action").to_numpy(zero_copy_only=False).astype(np.int64)
    episode_ids = np.array(table.column("episode_id").to_pylist(), dtype=object)
    src_arr     = np.array(table.column("agent_source").to_pylist(), dtype=object)
    config_keys = np.array(table.column("config_key").to_pylist(), dtype=object)

    features = np.concatenate([scalars, slots, word_hash, dims_active, sub_modes], axis=1)
    return BCDataset(features, actions, masks, episode_ids, src_arr, config_keys=config_keys)


def build_config_vocab(ds: BCDataset) -> dict[str, int]:
    """Assign a stable integer id to each distinct ``config_key`` in ``ds``.

    Index 0 is reserved for ``UNK_CONFIG_ID`` so runtime lookups of an
    unseen config can't collide with a real row. Sorting the keys first
    keeps the mapping deterministic across trainer invocations on the
    same data.
    """
    uniq = sorted({str(k) for k in ds.config_keys if str(k)})
    return {key: i + 1 for i, key in enumerate(uniq)}


def split_by_episode(
    ds: BCDataset,
    *,
    eval_fraction: float = 0.2,
    seed: int = 42,
) -> tuple[BCDataset, BCDataset, SplitStats]:
    """Split ``ds`` into train/eval by episode id (no row-level leakage).

    Episode assignment is a random shuffle seeded with ``seed`` so a
    trainer re-run lands on the same split. ``eval_fraction`` is a soft
    target — the actual fraction rounds to the nearest episode.
    """
    unique_eps = np.unique(ds.episode_ids)
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_eps)
    n_eval = max(1, int(round(len(unique_eps) * eval_fraction)))
    eval_eps = set(unique_eps[:n_eval])

    eval_mask = np.array([eid in eval_eps for eid in ds.episode_ids])
    train_mask = ~eval_mask

    def _subset(mask: np.ndarray) -> BCDataset:
        sub = BCDataset(
            features=ds.features[mask],
            actions=ds.actions[mask],
            masks=ds.masks[mask],
            episode_ids=ds.episode_ids[mask],
            sources=ds.sources[mask],
            config_keys=ds.config_keys[mask],
        )
        # Preserve any vocab binding the caller applied before splitting.
        sub.config_ids = ds.config_ids[mask]
        return sub

    train = _subset(train_mask)
    evl = _subset(eval_mask)

    sources: dict[str, int] = {}
    for s in ds.sources:
        sources[s] = sources.get(s, 0) + 1

    stats = SplitStats(
        num_train_rows=len(train),
        num_eval_rows=len(evl),
        num_train_episodes=len(unique_eps) - n_eval,
        num_eval_episodes=n_eval,
        sources=sources,
    )
    return train, evl, stats


def kfold_split_by_episode(
    ds: BCDataset,
    *,
    k: int,
    seed: int = 42,
) -> list[tuple[BCDataset, BCDataset, SplitStats]]:
    """Partition episodes into k disjoint folds and return all (train, eval, stats) triples.

    Shuffle-then-chunk: episodes are shuffled with ``seed`` so re-runs hit
    the same folds; ``np.array_split`` produces ``k`` groups whose sizes
    differ by at most one. Fold ``i``'s eval set is group ``i``; its train
    set is every other group concatenated.

    ``k`` must be ≤ number of unique episodes. The trainer clamps to
    leave-one-out above that.
    """
    unique_eps = np.unique(ds.episode_ids)
    if k < 2:
        raise ValueError(f"k must be ≥2 (got {k}) — use split_by_episode for single-split")
    if k > len(unique_eps):
        raise ValueError(
            f"k={k} exceeds number of episodes ({len(unique_eps)}) — "
            f"clamp to leave-one-out (k={len(unique_eps)}) before calling"
        )
    rng = np.random.default_rng(seed)
    rng.shuffle(unique_eps)
    fold_eps = np.array_split(unique_eps, k)

    sources_total: dict[str, int] = {}
    for s in ds.sources:
        sources_total[s] = sources_total.get(s, 0) + 1

    def _subset(mask: np.ndarray) -> BCDataset:
        sub = BCDataset(
            features=ds.features[mask],
            actions=ds.actions[mask],
            masks=ds.masks[mask],
            episode_ids=ds.episode_ids[mask],
            sources=ds.sources[mask],
            config_keys=ds.config_keys[mask],
        )
        sub.config_ids = ds.config_ids[mask]
        return sub

    folds: list[tuple[BCDataset, BCDataset, SplitStats]] = []
    for i in range(k):
        eval_eps = set(fold_eps[i].tolist())
        eval_mask = np.array([eid in eval_eps for eid in ds.episode_ids])
        train_mask = ~eval_mask
        train = _subset(train_mask)
        evl = _subset(eval_mask)
        stats = SplitStats(
            num_train_rows=len(train),
            num_eval_rows=len(evl),
            num_train_episodes=len(unique_eps) - len(eval_eps),
            num_eval_episodes=len(eval_eps),
            sources=sources_total,
        )
        folds.append((train, evl, stats))
    return folds
