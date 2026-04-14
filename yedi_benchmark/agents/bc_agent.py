"""BehaviorCloningAgent — loads a trained BC checkpoint and plays live.

The agent must featurize observations *exactly* the same way the trainer
did, or it'll predict nonsense. To guarantee parity we reuse the very
same functions ``featurizer.featurize_step`` uses offline, just wrapped
to accept the in-game ``(observation, info)`` the runner passes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..learning.dataset import OBS_DIM
from ..learning.featurizer import (
    NUM_ACTIONS,
    NUM_SLOTS,
    OBS_SCALAR_FIELDS,
    SLOT_FEATURE_DIM,
    WORD_HASH_DIM,
    _slot_features,
    hash_word,
    parse_active_dimensions,
)
from ..learning.model import BCModelConfig, BCPolicy
from .base_agent import BaseAgent


def _featurize_live(raw_state: dict) -> np.ndarray:
    """Build the same flat feature vector the trainer saw offline.

    Mirrors ``featurize_step`` but skips the action/reward/episode fields
    — those don't exist at inference time. Any divergence between this
    function and the offline featurizer will silently degrade the model,
    so the shared helpers (``_slot_features``, ``hash_word``) are the
    source of truth for both paths.
    """
    beat_phase = float(raw_state.get("beat_phase", 0) or 0)
    scalars = np.array(
        [float(raw_state.get(k, 0) or 0) for k in OBS_SCALAR_FIELDS],
        dtype=np.float32,
    )
    slots_data = raw_state.get("slots", []) or []
    slot_vecs: list[np.ndarray] = []
    word_vecs: list[np.ndarray] = []
    for i in range(NUM_SLOTS):
        slot = slots_data[i] if i < len(slots_data) else {}
        slot_vecs.append(_slot_features(slot, beat_phase))
        word = slot.get("word_value") if slot.get("occupied", False) else None
        word_vecs.append(hash_word(word))
    slots = np.concatenate(slot_vecs)
    word_hash = np.concatenate(word_vecs)
    dims_active = parse_active_dimensions(raw_state.get("config_key"))
    feats = np.concatenate([scalars, slots, word_hash, dims_active])
    assert feats.shape == (OBS_DIM,), f"feature dim drift: {feats.shape} vs {OBS_DIM}"
    return feats


class BehaviorCloningAgent(BaseAgent):
    """Loads a BC checkpoint and picks argmax of masked logits each step."""

    def __init__(self, checkpoint_path: str | Path, *, name: str = "bc",
                 device: str | None = None):
        super().__init__(name=name)
        # Imported here so the benchmark runner doesn't hard-require torch
        # for non-BC agents.
        import torch

        self._torch = torch
        self._device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        ckpt = torch.load(checkpoint_path, map_location=self._device,
                          weights_only=False)
        summary = ckpt.get("summary", {})
        # Feature-layout drift is the #1 way a BC checkpoint silently
        # breaks after a codebase change. Fail loud at load time instead.
        if summary.get("obs_dim", OBS_DIM) != OBS_DIM:
            raise ValueError(
                f"Checkpoint obs_dim={summary.get('obs_dim')} doesn't match "
                f"current featurizer OBS_DIM={OBS_DIM} — retrain after a "
                f"feature-layout change."
            )
        if summary.get("num_actions", NUM_ACTIONS) != NUM_ACTIONS:
            raise ValueError(
                f"Checkpoint num_actions={summary.get('num_actions')} doesn't "
                f"match current NUM_ACTIONS={NUM_ACTIONS}."
            )

        cfg = BCModelConfig(**ckpt["config"])
        self._model = BCPolicy(cfg).to(self._device)
        self._model.load_state_dict(ckpt["state_dict"])
        self._model.eval()
        self.summary = summary

    def act(self, observation: dict, info: dict = None) -> int:
        torch = self._torch
        info = info or {}
        raw = info.get("raw_state") or {}
        feats = _featurize_live(raw)

        mask_arr = observation.get("action_mask")
        if mask_arr is None:
            mask_arr = np.zeros(NUM_ACTIONS, dtype=np.float32)
            for a in raw.get("valid_actions", []) or []:
                a = int(a)
                if 0 <= a < NUM_ACTIONS:
                    mask_arr[a] = 1.0
        mask = np.asarray(mask_arr, dtype=np.float32)

        with torch.no_grad():
            f = torch.from_numpy(feats).unsqueeze(0).to(self._device)
            m = torch.from_numpy(mask).unsqueeze(0).to(self._device)
            logits = self._model(f, m)
            action = int(logits.argmax(dim=1).item())

        # Defensive fallback: if the mask was empty (no valid actions),
        # argmax returns whatever has the least-negative logit. Runner
        # is expected to terminate the episode in this state anyway, but
        # returning DRAW (always valid at game start) is a safe default.
        if mask.sum() == 0:
            return 0
        return action
