"""Turn replay-log events into fixed-shape numeric feature rows.

One step record in ``events.jsonl`` contains a ``raw_state`` dict plus
the action the agent took. This module converts that into a flat dict
of numpy arrays / scalars that a BC trainer can stack into tensors:

    {
        "episode_id":      str,
        "step":            int,
        "agent_name":      str,
        "agent_source":    str,      # human|greedy|random|llm
        "config_key":      str,
        "action":          int,
        "reward":          float,
        "terminated":      bool,
        "truncated":       bool,
        "mana":            float,    # scalar obs fields
        "mana_max":        float,
        "timer_remaining": float,
        "beat_phase":      float,
        "slots":           list[float],   # 7*11 = 77, row-major (matches yedi_env)
        "word_hash":       list[float],   # 7*64 = 448, row-major
        "dims_active":     list[float],   # 7, multi-hot over cognitive dimensions
        "sub_modes_active":list[float],   # 7, multi-hot over operator sub-modes
        "action_mask":     list[int],     # 37
    }

Design notes
------------
* **Layout parity with ``yedi_env._state_to_obs``**: the 7×11 slot layout
  is identical to the one the live environment hands to an agent, so a
  BC model trained on this output can drop into the Gymnasium env with
  zero rewiring.
* **Hash-bucket words**: ``slot.word_value`` is a free-form string. For
  v1 we hash it deterministically (md5, stable across Python runs) into
  a ``WORD_HASH_DIM``-wide one-hot vector. A real embedding upgrade is
  deferred — see the SL reminders memory note.
* **Memory-hidden cards**: when ``memory_hidden`` is true, the slot
  occupancy + the hidden flag are still emitted, but number/color/shape
  values come through as-is from the bridge. This mirrors live play:
  the memory dimension is encoded by the flag, not by zeroing features.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable, Iterator

import numpy as np


NUM_SLOTS: int = 7
"""7 slots: the 'new' slot + 6 board slots."""

DIMENSIONS: tuple[str, ...] = (
    "math", "visual", "spatial", "verbal", "music", "memory", "motor",
)
"""The 7 cognitive dimensions. Index order is the feature layout — don't
reorder without bumping the checkpoint version."""

DIMENSIONS_DIM: int = len(DIMENSIONS)

SUB_MODES: tuple[str, ...] = (
    "add", "subtract", "multiply",   # math / visual (color) operators
    "triangle", "rectangle",          # spatial shape targets
    "verbs", "nouns",                 # verbal part-of-speech targets
)
"""Known sub-mode tokens across all dimensions. The config_key for a game
like ``math:add+verbal:verbs`` contains both ``add`` and ``verbs``; this
multi-hot lets a single policy condition on the operator, not just the
dimension. Append-only — adding a new sub-mode is a breaking change
that bumps the checkpoint version."""

SUB_MODES_DIM: int = len(SUB_MODES)

SLOT_FEATURE_DIM: int = 11
"""Per-slot features, must match yedi_env._serialize_slots ordering.

    [occupied, card_mana, merges_done, is_super,
     number_val, color_r, color_g, color_b,
     shape_idx, memory_hidden, beat_phase]
"""

WORD_HASH_DIM: int = 64
"""One-hot hash-bucket dimension for slot.word_value."""

NUM_ACTIONS: int = 37
"""0 = DRAW, 1-30 = MOVE, 31-36 = SELL."""

OBS_SCALAR_FIELDS: tuple[str, ...] = (
    "mana",
    "mana_max",
    "timer_remaining",
    "beat_phase",
)


def parse_active_dimensions(config_key: str | None) -> np.ndarray:
    """Multi-hot encode the cognitive dimensions active in ``config_key``.

    ``config_key`` comes from ``ScoreManager.BuildConfigKey`` and looks
    like ``"math:add+memory:every action"`` — sorted, '+'-joined
    ``dim:mode`` pairs. We tokenize on any non-alphanumeric run so both
    ``:`` and ``-`` separators parse the same way (tests historically
    used hyphens). Unknown tokens (sub-mode names) are ignored.

    Giving the model a direct signal about which dimensions are "live"
    lets it learn dimension-specific policies (attend to ``number_value``
    when math is on, to ``word_value`` when verbal is on) instead of
    inferring the mode from state every step.
    """
    vec = np.zeros(DIMENSIONS_DIM, dtype=np.float32)
    if not config_key:
        return vec
    tokens = set(re.findall(r"[a-z0-9]+", config_key.lower()))
    for i, dim in enumerate(DIMENSIONS):
        if dim in tokens:
            vec[i] = 1.0
    return vec


def parse_sub_modes(config_key: str | None) -> np.ndarray:
    """Multi-hot encode the sub-modes (operators) active in ``config_key``.

    Without this, ``math:add`` and ``math:multiply`` produce identical
    ``dims_active`` vectors — the model only sees "math is on" and can't
    condition behaviour on the operator. We tokenize the same way
    ``parse_active_dimensions`` does so both paths handle the various
    ``:`` / ``+`` / hyphen separators uniformly.
    """
    vec = np.zeros(SUB_MODES_DIM, dtype=np.float32)
    if not config_key:
        return vec
    tokens = set(re.findall(r"[a-z0-9]+", config_key.lower()))
    for i, sub in enumerate(SUB_MODES):
        if sub in tokens:
            vec[i] = 1.0
    return vec


def classify_agent_source(agent_name: str) -> str:
    """Best-effort provider classification from the recorded ``agent_name``.

    Registered agent names are free-form, but the baselines follow a
    naming convention (``Human-1``, ``Greedy``, ``Random``) that lets us
    tag rows without joining against the registry at export time. LLM
    agents are anything else — good enough to filter in a trainer.
    """
    if not agent_name:
        return "unknown"
    lower = agent_name.lower()
    if "human" in lower:
        return "human"
    if "greedy" in lower:
        return "greedy"
    if "random" in lower:
        return "random"
    return "llm"


def hash_word(word: str | None, dim: int = WORD_HASH_DIM) -> np.ndarray:
    """Deterministic one-hot hash of ``word`` into a ``dim``-wide vector.

    Empty / None / whitespace-only inputs produce an all-zero vector so
    downstream code can treat "no word" as an absent feature. We use md5
    rather than Python's ``hash()`` because PYTHONHASHSEED randomisation
    would otherwise make exported datasets non-reproducible across runs.
    """
    out = np.zeros(dim, dtype=np.float32)
    if not word:
        return out
    token = word.strip().lower()
    if not token:
        return out
    digest = hashlib.md5(token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "little") % dim
    out[bucket] = 1.0
    return out


def _slot_features(slot: dict, beat_phase: float) -> np.ndarray:
    """11-d slot vector matching yedi_env._serialize_slots exactly."""
    vec = np.zeros(SLOT_FEATURE_DIM, dtype=np.float32)
    if not slot.get("occupied", False):
        return vec
    vec[0] = 1.0
    vec[1] = float(slot.get("card_mana", 0) or 0)
    vec[2] = float(slot.get("merges_done", 0) or 0)
    vec[3] = 0.0  # is_super — bridge doesn't emit yet; keep slot for parity
    vec[4] = float(slot.get("number_value", 0) or 0)
    vec[5] = float(slot.get("color_r", 0) or 0)
    vec[6] = float(slot.get("color_g", 0) or 0)
    vec[7] = float(slot.get("color_b", 0) or 0)
    vec[8] = float(slot.get("shape_index", 0) or 0)
    vec[9] = 1.0 if slot.get("memory_hidden", False) else 0.0
    vec[10] = float(beat_phase)
    return vec


def _action_mask_from_state(state: dict) -> np.ndarray:
    """Recover the 37-wide legal-action mask from the raw state.

    Step records carry ``observation.action_mask`` directly, but fall
    back to reconstructing from ``raw_state.valid_actions`` so offline
    processing still works on logs that lost the obs payload.
    """
    mask = np.zeros(NUM_ACTIONS, dtype=np.int8)
    for a in state.get("valid_actions", []) or []:
        a = int(a)
        if 0 <= a < NUM_ACTIONS:
            mask[a] = 1
    return mask


def featurize_step(
    step: dict,
    *,
    episode_id: str,
    agent_name: str,
    agent_source: str,
) -> dict[str, Any]:
    """Convert one ``step`` event into a flat feature dict.

    Returns ``None`` only if ``raw_state`` is missing — old logs from
    early runs don't carry it and can't be featurized.
    """
    raw = step.get("raw_state")
    if not raw:
        return None  # type: ignore[return-value]

    obs = step.get("observation", {}) or {}
    beat_phase = float(raw.get("beat_phase", 0) or 0)

    slots_data = raw.get("slots", []) or []
    slot_vecs: list[np.ndarray] = []
    word_vecs: list[np.ndarray] = []
    for i in range(NUM_SLOTS):
        slot = slots_data[i] if i < len(slots_data) else {}
        slot_vecs.append(_slot_features(slot, beat_phase))
        word = slot.get("word_value") if slot.get("occupied", False) else None
        word_vecs.append(hash_word(word))

    slots_flat = np.concatenate(slot_vecs).tolist()
    word_hash_flat = np.concatenate(word_vecs).tolist()
    config_key = str(raw.get("config_key", "") or "")
    dims_active = parse_active_dimensions(config_key).tolist()
    sub_modes_active = parse_sub_modes(config_key).tolist()

    # Prefer the pre-serialized mask the agent actually saw; fall back
    # only when the observation payload isn't in the log.
    mask_from_obs = obs.get("action_mask")
    if mask_from_obs is not None:
        action_mask = list(map(int, mask_from_obs))
    else:
        action_mask = _action_mask_from_state(raw).tolist()

    return {
        "episode_id":      episode_id,
        "step":            int(step.get("step", 0)),
        "agent_name":      agent_name,
        "agent_source":    agent_source,
        "config_key":      config_key,
        "action":          int(step["action"]),
        "reward":          float(step.get("reward", 0.0) or 0.0),
        "terminated":      bool(step.get("terminated", False)),
        "truncated":       bool(step.get("truncated", False)),
        "mana":            float(raw.get("mana", 0) or 0),
        "mana_max":        float(raw.get("mana_max", 0) or 0),
        "timer_remaining": float(raw.get("timer_remaining", 0) or 0),
        "beat_phase":      beat_phase,
        "slots":           slots_flat,
        "word_hash":       word_hash_flat,
        "dims_active":     dims_active,
        "sub_modes_active": sub_modes_active,
        "action_mask":     action_mask,
    }


def featurize_episode(events: Iterable[dict]) -> Iterator[dict[str, Any]]:
    """Yield one (pre-state, action) feature row per usable transition.

    **State-shift invariant**: the replay logger records each step's
    ``raw_state`` and ``observation`` *after* the action was applied,
    but BC wants to predict ``action_k`` from the state the agent saw
    *before* picking it — i.e. the post-state of step ``k-1``. So for
    an episode with N step records we emit N-1 rows, pairing
    ``step[i-1].raw_state`` (pre-state for action i) with
    ``step[i].action`` (the label).

    The first action (step 0) is dropped because we don't log the
    pre-episode reset state. That's usually DRAW anyway, so the loss
    is small, but the featurizer can be swapped to the (pre, action)
    schema without pipeline churn once the runner starts logging it
    explicitly.

    ``action_mask`` for the pair comes from the *pre-state*'s
    ``valid_actions`` — which was the actual legal set at decision
    time. Mis-aligning the mask with the action (e.g. using step[i]'s
    post-action mask) gives BC a training signal where the expert's
    chosen action is frequently "illegal", and cross-entropy on a
    -1e9 logit explodes the loss.
    """
    episode_id = ""
    agent_name = "unknown"
    agent_source = "unknown"
    pending: list[dict] = []

    for ev in events:
        etype = ev.get("type")
        if etype == "episode_start":
            episode_id = ev.get("episode_id", "")
            agent_name = ev.get("agent_name", "unknown")
            agent_source = classify_agent_source(agent_name)
            pending.clear()
            continue
        if etype == "step":
            pending.append(ev)
            continue
        # episode_end / screenshot / other: ignore

    if len(pending) < 2:
        return

    for i in range(1, len(pending)):
        prev_step = pending[i - 1]
        next_step = pending[i]

        prev_raw = prev_step.get("raw_state")
        prev_obs = prev_step.get("observation") or {}
        if not prev_raw:
            continue

        pair_record = {
            "step":       next_step.get("step", i),
            "action":     next_step.get("action", 0),
            "reward":     next_step.get("reward", 0.0),
            "terminated": next_step.get("terminated", False),
            "truncated":  next_step.get("truncated", False),
            "observation": prev_obs,
            "raw_state":   prev_raw,
        }
        row = featurize_step(
            pair_record,
            episode_id=episode_id,
            agent_name=agent_name,
            agent_source=agent_source,
        )
        if row is None:
            continue
        # Rows where ``action`` isn't in the pre-state ``action_mask``
        # happen occasionally (bridge valid_actions can lag a frame,
        # especially on the human path). We keep them: BC trains
        # unmasked, so a stale mask no longer corrupts the loss, and
        # throwing the row away would drop real demonstrations.
        yield row
