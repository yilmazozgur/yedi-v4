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
  4. Fallback → first valid action (or WAIT).

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
ACTION_WAIT = 37


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

# Neutral values by number mode — a merged card with this value is dead
# weight (adds/multiplies nothing) and should be sold to free the slot.
_NUMBER_NEUTRAL = {
    "add": 0.0,
    "multiply": 1.0,
}


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
        # A merged card that reached the identity value for its mode
        # (0 for add, 1 for multiply) can never improve another card.
        # Selling it frees the slot for productive merges.
        number_mode = raw_state.get("mode_number", "")
        neutral_val = _NUMBER_NEUTRAL.get(number_mode)
        if neutral_val is not None:
            for build_idx, slot in enumerate(build_slots, start=1):
                if not slot.get("occupied"):
                    continue
                merges = int(slot.get("merges_done", 0) or 0)
                if merges == 0:
                    continue  # Only sell merged cards that became neutral
                nv = float(slot.get("number_value", -9999))
                if nv == neutral_val:
                    action = _sell_action(build_idx)
                    if not valid_actions or action in valid_actions:
                        logger.debug(
                            "greedy: sell neutral slot %d (num=%s, mode=%s, action %d)",
                            build_idx, nv, number_mode, action,
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
        return ACTION_WAIT

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
