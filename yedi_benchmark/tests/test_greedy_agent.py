"""Tests for the GreedyAgent baseline + the env.preview_merge wrapper.

We never start a real bridge or browser here. Tests build raw_state dicts
shaped like AgentBridge.SerializeGameState output (slots + merge_previews +
mode_*). The wrapper tests reuse the YediEnv.__new__ + fake-websocket
pattern from test_bridge_failures.py so the wrapper goes through the real
_send_command path without touching a real socket.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from yedi_benchmark.agents.greedy_agent import (
    ACTION_DRAW,
    ACTION_WAIT,
    GreedyAgent,
    _min_active_gain,
    _move_action,
    _sell_action,
)
from yedi_benchmark.yedi_env import YediEnv


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _slot(occupied=False, merges_done=0, **extra):
    s = {"occupied": occupied, "merges_done": merges_done}
    s.update(extra)
    return s


def _preview(source, target, **gains):
    """Build one merge_previews entry. ``target`` is the slot number (1..5);
    the action ID is computed from source/target the same way the bridge
    does it."""
    src_idx = 0 if source == "new" else int(source)
    dst_num = int(target)
    entry = {
        "source": source,
        "target": target,
        "action": 1 + src_idx * 5 + (dst_num - 1),
        "number_gain": 0.0,
        "color_gain": 0.0,
        "shape_gain": 0.0,
        "word_gain": 0.0,
    }
    entry.update(gains)
    return entry


def _state(slots, modes=None, valid_actions=None, merge_previews=None):
    """Build a raw_state dict shaped like AgentBridge.SerializeGameState output.

    ``slots`` must be length 7 (new + 5 build slots + sell). The greedy agent
    only inspects slots 0..5 so the trailing slot can be a stub.
    """
    modes = modes or {"number": "add"}
    out = {
        "slots": slots,
        "valid_actions": valid_actions,  # None == "no mask, anything goes"
        "merge_previews": merge_previews or [],
    }
    for dim in ("number", "color", "shape", "word"):
        out[f"mode_{dim}"] = modes.get(dim, "")
    return out


def _info(slots, modes=None, valid_actions=None, merge_previews=None):
    return {"raw_state": _state(slots, modes=modes, valid_actions=valid_actions,
                                merge_previews=merge_previews)}


def _empty_obs():
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# Pure helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestActionEncoders:
    def test_move_new_to_slot_1(self):
        # new (idx 0) → slot 1 ⇒ action 1
        assert _move_action(0, 1) == 1

    def test_move_new_to_slot_5(self):
        assert _move_action(0, 5) == 5

    def test_move_slot_1_to_slot_2(self):
        # src_idx=1 (slot 1) → dst 2 ⇒ 1 + 5 + 1 = 7
        assert _move_action(1, 2) == 7

    def test_sell_new(self):
        assert _sell_action(0) == 31

    def test_sell_slot_5(self):
        assert _sell_action(5) == 36


class TestMinActiveGain:
    def test_single_dim(self):
        preview = {"number_gain": 2.0, "color_gain": -1.0}
        assert _min_active_gain(preview, ["number"]) == 2.0

    def test_min_across_dims(self):
        preview = {"number_gain": 3.0, "color_gain": 1.0, "shape_gain": 2.0}
        assert _min_active_gain(preview, ["number", "color", "shape"]) == 1.0

    def test_negative_dominates(self):
        preview = {"number_gain": 3.0, "color_gain": -1.0}
        assert _min_active_gain(preview, ["number", "color"]) == -1.0

    def test_no_active_dims_falls_back_to_number(self):
        # Defensive path: if no dim is active we fall back to number_gain so
        # we still pick the best math merge instead of returning 0 for everything.
        preview = {"number_gain": 2.0}
        assert _min_active_gain(preview, []) == 2.0


# ──────────────────────────────────────────────────────────────────────────────
# GreedyAgent decision logic
# ──────────────────────────────────────────────────────────────────────────────


class TestGreedyAgentDecisions:
    def test_draws_when_new_is_empty(self):
        slots = [_slot(False)] + [_slot(False)] * 5 + [_slot(False)]
        agent = GreedyAgent()
        action = agent.act(_empty_obs(), _info(slots))
        assert action == ACTION_DRAW

    def test_sells_maxed_out_build_slot_first(self):
        # Slot 1 is at the 3-merge cap → must SELL it before doing anything else.
        slots = [
            _slot(True),                       # new (occupied, irrelevant)
            _slot(True, merges_done=3),        # slot 1 — MAXED
            _slot(True, merges_done=0),        # slot 2
            _slot(False),                      # slot 3
            _slot(False),                      # slot 4
            _slot(False),                      # slot 5
            _slot(False),                      # sell slot
        ]
        # The bridge would not include a preview entry for the maxed slot
        # (the merge would be rejected), but we throw one in anyway to verify
        # the sell-first rule wins regardless.
        previews = [_preview("new", "2", number_gain=3.0)]
        agent = GreedyAgent()
        action = agent.act(_empty_obs(), _info(slots, merge_previews=previews))
        assert action == _sell_action(1)  # 32

    def test_picks_best_merge_by_min_active_gain(self):
        # Two occupied build slots. Slot 1 gives a strong number+ok color,
        # slot 2 gives a perfect number but -1 color (dominates the min).
        # The min-rule must pick slot 1, even though slot 2 has a higher max.
        slots = [
            _slot(True),                       # new
            _slot(True, merges_done=0),        # slot 1
            _slot(True, merges_done=0),        # slot 2
            _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [
            _preview("new", "1", number_gain=2.0, color_gain=1.0),
            _preview("new", "2", number_gain=3.0, color_gain=-1.0),
        ]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(),
            _info(slots, modes={"number": "add", "color": "add"},
                  merge_previews=previews),
        )
        assert action == _move_action(0, 1)  # 1

    def test_skips_target_at_merge_cap(self):
        # The bridge already filters out merges to maxed targets — it just
        # doesn't include them in merge_previews. Greedy must respect that
        # and pick whatever IS in the previews list, not invent a candidate.
        slots = [
            _slot(True),
            _slot(True, merges_done=2),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        # Only the slot 2 candidate is shipped (slot 1 is excluded by the
        # bridge because its target was at the merge cap).
        previews = [_preview("new", "2", number_gain=1.0)]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        assert action == _move_action(0, 2)  # 2

    def test_places_into_empty_slot_when_no_good_merge(self):
        # The only occupied build slot offers a -1 (bad) merge — below the
        # threshold. Greedy should preserve mana by placing into an empty
        # slot rather than committing the bad merge.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(False),                      # slot 2 empty
            _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [_preview("new", "1", number_gain=-1.0)]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        assert action == _move_action(0, 2)  # place into empty slot 2

    def test_sells_new_when_every_slot_full_and_no_good_merge(self):
        # All five build slots occupied, every preview returns -1. No empty
        # slot to escape into → sell the new card to recover some mana.
        slots = [_slot(True)]
        for _ in range(5):
            slots.append(_slot(True, merges_done=0))
        slots.append(_slot(False))
        previews = [
            _preview("new", str(i), number_gain=-1.0) for i in range(1, 6)
        ]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        assert action == _sell_action(0)  # 31

    def test_threshold_zero_accepts_neutral_merge(self):
        # With threshold=0, a 0 (neutral) merge is acceptable.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [_preview("new", "1", number_gain=0.0)]
        agent = GreedyAgent(merge_threshold=0)
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        assert action == _move_action(0, 1)

    def test_threshold_two_rejects_ok_merge(self):
        # With threshold=2 (great-or-better), an "ok" (1) merge is rejected
        # in favour of placing into an empty slot.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [_preview("new", "1", number_gain=1.0)]
        agent = GreedyAgent(merge_threshold=2)
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        # Slot 2 is empty → preserve potential
        assert action == _move_action(0, 2)

    def test_ignores_inter_slot_merges(self):
        # The bridge ships slot_a → slot_b previews too, but greedy only
        # cares about the new→build_slot lookahead (per the module docstring).
        # If the only entries are inter-slot, greedy must NOT pick them — it
        # falls through to the place / sell path instead.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [
            # Only inter-slot, no new→* entries.
            _preview("1", "2", number_gain=3.0),
            _preview("2", "1", number_gain=3.0),
        ]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        # Both merges look great but greedy ignores them. With slot 3 empty,
        # it should place new into slot 3.
        assert action == _move_action(0, 3)

    def test_respects_action_mask(self):
        # The merge action for slot 1 is not in the valid_actions set →
        # greedy must not pick it even though slot 1 is occupied.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [
            _preview("new", "1", number_gain=3.0),
            _preview("new", "2", number_gain=1.0),
        ]
        valid = [_move_action(0, 2)]  # only "merge new → slot 2" is allowed
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(),
            _info(slots, modes={"number": "add"},
                  valid_actions=valid, merge_previews=previews),
        )
        assert action == _move_action(0, 2)

    def test_fallback_to_wait_when_only_wait_is_valid(self):
        # New is empty but DRAW isn't in the mask — and WAIT is the only
        # valid action. Greedy must fall through to step 4 and pick WAIT
        # rather than crashing or returning an invalid action.
        slots = [_slot(False)] * 7
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, valid_actions=[ACTION_WAIT]),
        )
        assert action == ACTION_WAIT

    def test_min_across_active_dims_only(self):
        # color_gain is -1, but color is NOT active → it must NOT influence
        # the decision. Number is the only active dim, so the merge should
        # be accepted.
        slots = [
            _slot(True),
            _slot(True, merges_done=0),
            _slot(False), _slot(False), _slot(False), _slot(False),
            _slot(False),
        ]
        previews = [
            _preview("new", "1", number_gain=2.0, color_gain=-99.0),
        ]
        agent = GreedyAgent()
        action = agent.act(
            _empty_obs(), _info(slots, modes={"number": "add"}, merge_previews=previews),
        )
        assert action == _move_action(0, 1)


# ──────────────────────────────────────────────────────────────────────────────
# YediEnv.preview_merge wrapper
# ──────────────────────────────────────────────────────────────────────────────
#
# Greedy no longer uses this wrapper (it reads merge_previews from the state
# response directly), but the wrapper is kept as a debug / ad-hoc inspection
# tool: it scores a single arbitrary merge on demand. Tests guarantee the
# command/response shape stays stable.


def _make_env_with_response(payload: dict) -> YediEnv:
    """Build a YediEnv with a fake ws/loop wired in (no real bridge).

    Mirrors the helper in test_bridge_failures.py — we bypass __init__ and
    plug in a MagicMock websocket whose recv() returns the canned payload.
    """
    env = YediEnv.__new__(YediEnv)
    env._loop = asyncio.new_event_loop()

    fake_ws = MagicMock()
    fake_ws.send = AsyncMock()
    fake_ws.recv = AsyncMock(return_value=json.dumps(payload))
    env._ws = fake_ws
    return env


class TestPreviewMergeWrapper:
    def test_returns_bridge_response_dict(self):
        payload = {
            "type": "merge_preview",
            "source": "new",
            "target": "1",
            "number_gain": 2.0,
            "color_gain": 1.0,
            "shape_gain": 0.0,
            "word_gain": 0.0,
            "target_can_accept_merge": True,
            "target_merges_done": 1,
            "target_merges_max": 3,
            "mana": 200,  # so _send_command treats this as a state-bearing OK
            "seq": 1,
        }
        env = _make_env_with_response(payload)
        try:
            result = env.preview_merge("new", "1")
            assert result["number_gain"] == 2.0
            assert result["target_can_accept_merge"] is True
            # The wrapper sent a preview_merge command (not draw_card etc.)
            sent = json.loads(env._ws.send.await_args.args[0])
            assert sent["type"] == "preview_merge"
            assert sent["source"] == "new"
            assert sent["target"] == "1"
        finally:
            env._loop.close()

    def test_propagates_bridge_errors(self):
        from yedi_benchmark.yedi_env import BridgeDisconnectedError

        # Bare {"error": ..., "seq": ...} payload — _send_command treats it as
        # a fatal bridge error and raises BridgeDisconnectedError.
        env = _make_env_with_response({"error": "target at merge cap", "seq": 1})
        try:
            with pytest.raises(BridgeDisconnectedError, match="target at merge cap"):
                env.preview_merge("new", "1")
        finally:
            env._loop.close()
