"""Greedy 1-step lookahead agent — strong programmatic baseline.

This is the calibration baseline between RandomAgent and the LLM agents. It
reads the bridge's pre-computed ``merge_previews`` field from the observation
(populated by ``AgentBridge.SerializeGameState``) which scores every legal
merge candidate using the SAME ``ComputeMerge*Gain`` code the real game
uses, so the scores are guaranteed to match. No extra round-trip per
decision.

Why "highest minimum" and not "highest sum / average":
- Multipliers compound multiplicatively across dimensions, so the final gain
  is bounded by the worst factor. A merge that's 3 (perfect) in math but -1
  (loss) in colour is a net loss, regardless of how strong the math leg is.
- This matches the DECISION RULE block in the LLM system prompt, so the
  greedy agent and the LLM are being graded against the same heuristic.

Decision priority each turn (mirrors the CORE_RULES checklist):
  1. If any build slot has hit its merge cap → SELL it.
  2. If the "new" slot is occupied:
       a. Score every new→slot_n preview entry.
       b. If the best score is >= 1 (ok or better) in EVERY active dim → merge.
       c. Else if there's an empty build slot → place into it (preserves mana).
       d. Else → sell the new card rather than ruin a built slot.
  3. Else (new is empty) → DRAW.
  4. Fallback → first valid action (or DRAW).

The greedy agent does NOT consider inter-slot merges (slot_a → slot_b) even
though the bridge ships those previews too. The "new card lookahead" is the
dominant decision in practice, and inter-slot merges roughly double the
search space without obviously improving play.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base_agent import BaseAgent

logger = logging.getLogger("greedy_agent")


# Action IDs
ACTION_DRAW = 0


def _move_action(src_idx: int, dst_num: int) -> int:
    """src_idx in 0..5 (0=new, 1..5=build slots), dst_num in 1..5."""
    return 1 + src_idx * 5 + (dst_num - 1)


def _sell_action(src_idx: int) -> int:
    """src_idx in 0..5 (0=new, 1..5=build slots)."""
    return 31 + src_idx


# Active-dim helpers ----------------------------------------------------------
#
# raw_state carries the active mode for each dimension as "mode_<dim>" — empty
# string when the dimension isn't active. The merge_preview entries always
# carry a gain for every dimension; we filter to the active ones when computing
# the min-multiplier across dims.

_DIM_TO_GAIN_KEY = {
    "number": "number_gain",
    "color":  "color_gain",
    "shape":  "shape_gain",
    "word":   "word_gain",
}

# Neutral-value registry ---------------------------------------------------
#
# Maps (dimension, mode) → either a (field_name, value) tuple for exact
# slot-field match, or a callable(slot_dict) → bool for multi-field checks.
# A merged card at the neutral/identity for ALL active dims can never
# improve another card — sell it to free the slot.
#
# "number:sort" and "word:scrabble" intentionally omitted (no identity).


def _slot_is_white(slot: dict) -> bool:
    """RGB all-ones → White (add/gray/text identity)."""
    try:
        return (float(slot.get("color_r", -1)) == 1.0
                and float(slot.get("color_g", -1)) == 1.0
                and float(slot.get("color_b", -1)) == 1.0)
    except (TypeError, ValueError):
        return False


def _slot_is_black(slot: dict) -> bool:
    """RGB all-zeros → Black (subtract identity)."""
    try:
        return (float(slot.get("color_r", -1)) == 0.0
                and float(slot.get("color_g", -1)) == 0.0
                and float(slot.get("color_b", -1)) == 0.0)
    except (TypeError, ValueError):
        return False


_NEUTRAL_REGISTRY: dict = {
    # Number modes
    ("number", "add"):         ("number_value", 0.0),
    ("number", "multiply"):    ("number_value", 1.0),
    ("number", "gcd"):         ("number_value", 1.0),
    ("number", "trigon"):      ("number_value", 0.0),
    ("number", "vector"):      ("number_value", 0.0),
    ("number", "interval"):    ("number_value", 0.0),
    # Color modes
    ("color", "add"):          _slot_is_white,
    ("color", "subtract"):     _slot_is_black,
    ("color", "gray"):         _slot_is_white,
    ("color", "text"):         _slot_is_white,
    # Shape modes — identity index (NOT the blank/reset index).
    # triangle/rectangle/triple/kanizsa: 7 = empty-set symbol (blank=8)
    # sphere: 0 = neutral angle (blank=10)
    # hanoi: 9 = solved state (blank=16)
    ("shape", "triangle"):     ("shape_index", 7),
    ("shape", "rectangle"):    ("shape_index", 7),
    ("shape", "kanizsa"):      ("shape_index", 7),
    ("shape", "hanoi"):        ("shape_index", 9),
    ("shape", "triple"):       ("shape_index", 7),
    ("shape", "sphere"):       ("shape_index", 0),
    # Word modes (all except scrabble — no single neutral)
    ("word", "verbs"):         ("word_value", "nihil"),
    ("word", "nouns"):         ("word_value", "nihil"),
    ("word", "adjectives"):    ("word_value", "nihil"),
    ("word", "synVerbs"):      ("word_value", "nihil"),
    ("word", "synAdjectives"): ("word_value", "nihil"),
    ("word", "grammar"):       ("word_value", "nihil"),
    ("word", "questions"):     ("word_value", "nihil"),
}


def _check_dim_neutral(slot: dict, dim: str, mode: str) -> bool:
    """True if the slot card is at the neutral/identity for (dim, mode)."""
    checker = _NEUTRAL_REGISTRY.get((dim, mode))
    if checker is None:
        return False  # unknown mode — can't determine neutral
    if callable(checker):
        return checker(slot)
    field, value = checker
    try:
        slot_val = slot.get(field)
        if slot_val is None:
            return False
        if isinstance(value, float):
            return float(slot_val) == value
        elif isinstance(value, int):
            return int(slot_val) == value
        return str(slot_val) == str(value)
    except (TypeError, ValueError):
        return False


def _is_slot_neutral(slot: dict, raw_state: dict) -> bool:
    """True if slot card is at neutral in ALL active dimensions.

    A card neutral in every active dim can never improve another card
    through further merges (except the 2.5× PERFECT pairing with another
    neutral, which the greedy agent doesn't pursue). Selling it frees the
    slot for productive merges.
    """
    checked = 0
    for dim in _DIM_TO_GAIN_KEY:
        mode = raw_state.get(f"mode_{dim}", "")
        if not mode:
            continue
        checked += 1
        if not _check_dim_neutral(slot, dim, mode):
            return False
    return checked > 0


def _active_dims(raw_state: dict) -> list[str]:
    out = []
    for dim in _DIM_TO_GAIN_KEY:
        if raw_state.get(f"mode_{dim}"):
            out.append(dim)
    return out


def _min_active_gain(preview: dict, active: list[str]) -> float:
    """Smallest gain tier across the active dimensions (worst-case bound)."""
    if not active:
        # Defensive: no active dim → fall back to the number gain so the
        # agent at least picks the best math merge it can find.
        return float(preview.get("number_gain", 0.0))
    return min(float(preview.get(_DIM_TO_GAIN_KEY[d], 0.0)) for d in active)


# Greedy agent -----------------------------------------------------------------


class GreedyAgent(BaseAgent):
    """Programmatic baseline that scores merges via the bridge's pre-computed
    merge_previews block.

    Args:
        merge_threshold: minimum acceptable per-dim gain tier for a merge to
            be considered "worth it". Default 1 = "ok or better in every
            active dim". Lower this to 0 for a more aggressive agent that
            also accepts neutral merges, or raise to 2 for a strict "great
            or better" agent.
        name: agent name (used for logging and replay).
    """

    def __init__(
        self,
        merge_threshold: int = 1,
        name: str = "greedy",
    ):
        super().__init__(name=name)
        self._merge_threshold = merge_threshold

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    def act(self, observation: dict, info: dict = None) -> int:
        info = info or {}
        raw_state = info.get("raw_state") or {}
        slots = raw_state.get("slots") or []
        valid_actions = set(raw_state.get("valid_actions") or [])
        active = _active_dims(raw_state)
        previews = raw_state.get("merge_previews") or []

        # Index slots by their position in the SerializeGameState array:
        #   0 = new, 1..5 = build slots, 6 = sell
        # We only care about new (0) and build slots (1..5).
        new_slot = slots[0] if len(slots) > 0 else {}
        build_slots = []
        for i in range(1, 6):
            build_slots.append(slots[i] if i < len(slots) else {})

        # ---------------- 1. Sell any maxed-out build slot --------------
        for build_idx, slot in enumerate(build_slots, start=1):
            if not slot.get("occupied"):
                continue
            merges = int(slot.get("merges_done", 0) or 0)
            # The bridge exposes maxNumberOfMerges as a per-card constant.
            # We don't get it in the slot serializer, so we hard-code the
            # game's well-known limit of 3.
            if merges >= 3:
                action = _sell_action(build_idx)  # 31..36
                if not valid_actions or action in valid_actions:
                    logger.debug("greedy: sell maxed slot %d (action %d)", build_idx, action)
                    return action

        # ---------------- 1b. Sell neutral cards ----------------------
        # A merged card that reached the identity value in ALL active
        # dimensions can never improve another card.  Selling it frees
        # the slot for productive merges.
        for build_idx, slot in enumerate(build_slots, start=1):
            if not slot.get("occupied"):
                continue
            merges = int(slot.get("merges_done", 0) or 0)
            if merges == 0:
                continue  # Only sell merged cards that became neutral
            if _is_slot_neutral(slot, raw_state):
                action = _sell_action(build_idx)
                if not valid_actions or action in valid_actions:
                    logger.debug(
                        "greedy: sell neutral slot %d (action %d)",
                        build_idx, action,
                    )
                    return action

        # ---------------- 2. Place / merge / sell the "new" card --------
        if new_slot.get("occupied"):
            best = self._best_merge_for_new(previews, valid_actions, active)
            if best is not None:
                best_score, best_action = best
                if best_score >= self._merge_threshold:
                    logger.debug(
                        "greedy: merge new → action %d (min-gain %s, threshold %s)",
                        best_action, best_score, self._merge_threshold,
                    )
                    return best_action

            # No good merge — prefer placing into an empty build slot
            for build_idx, slot in enumerate(build_slots, start=1):
                if slot.get("occupied"):
                    continue
                action = _move_action(0, build_idx)  # new → empty slot
                if not valid_actions or action in valid_actions:
                    logger.debug(
                        "greedy: place new → empty slot %d (action %d)",
                        build_idx, action,
                    )
                    return action

            # Every slot full and no good merge — sell the new card to
            # recover most of the draw cost rather than degrading a slot.
            sell_new = _sell_action(0)  # 31
            if not valid_actions or sell_new in valid_actions:
                logger.debug("greedy: sell new (action 31) — no good merge available")
                return sell_new

            # Last-resort merge: even if it's below threshold, do it rather
            # than nothing. This only fires when sell_new is somehow invalid.
            if best is not None:
                logger.debug(
                    "greedy: forced sub-threshold merge action %d (score %s)",
                    best[1], best[0],
                )
                return best[1]

        # ---------------- 3. New is empty — DRAW ------------------------
        if not new_slot.get("occupied") and (
            not valid_actions or ACTION_DRAW in valid_actions
        ):
            logger.debug("greedy: draw")
            return ACTION_DRAW

        # ---------------- 4. Fallback ----------------------------------
        if valid_actions:
            return min(valid_actions)
        return ACTION_DRAW

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _best_merge_for_new(
        self,
        previews: list,
        valid_actions: set,
        active: list,
    ) -> Optional[tuple]:
        """Pick the best (score, action) among new→build_slot preview entries.

        Returns None if no eligible new→slot entry exists in the previews.
        Inter-slot entries (slot_a→slot_b) are intentionally ignored — see
        the module docstring for why.
        """
        best: Optional[tuple] = None
        for entry in previews:
            if entry.get("source") != "new":
                continue
            action = entry.get("action")
            if action is None:
                continue
            if valid_actions and action not in valid_actions:
                continue

            score = _min_active_gain(entry, active)
            if best is None or score > best[0]:
                best = (score, action)

        return best
