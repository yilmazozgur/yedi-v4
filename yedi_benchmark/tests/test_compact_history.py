"""Tests for compact-history mode (Mode C: metadata-c / vision-c).

Three layers:
  1. Pure helpers — _compact_slot, _compact_slots_row, _annotate_action,
     format_trail_entry. These should be deterministic and lossless for
     the dimensions the agent cares about.
  2. build_system_prompt with include_history_legend=True — the legend must
     be present and only when asked.
  3. LLMAgent end-to-end with the StubProvider — verify the trail is built
     across steps, prefixed to the next prompt, error paths still log, and
     reset() clears it between episodes.
"""

from __future__ import annotations

import numpy as np
import pytest

from yedi_benchmark.agents.llm_agent import (
    LLMAgent,
    MAX_HISTORY_TURNS,
    _annotate_action,
    _compact_slot,
    _compact_slots_row,
    build_system_prompt,
    format_trail_entry,
)
from yedi_benchmark.providers.base import LLMProvider
from yedi_benchmark.registries.default_prompt import get_default_prompt


# ──────────────────────────────────────────────────────────────────────────────
# Helpers (mirrors test_prompt_assembly.py so the two files stay readable
# in isolation)
# ──────────────────────────────────────────────────────────────────────────────


class StubProvider(LLMProvider):
    def __init__(self, reply: str = "0"):
        super().__init__(model="stub-model", max_tokens=64, supports_vision=False)
        self.reply = reply
        self.calls: list[dict] = []

    def complete(self, messages, system=None, should_cancel=None):
        self.calls.append({
            "messages": messages, "system": system, "should_cancel": should_cancel,
        })
        return self.reply


def _slot_card(num=None, color=None, shape=None, word=None,
               mana=9, merges=0, hidden=False):
    """Build a slot dict the agent's encoders accept."""
    s = {"occupied": True, "card_mana": mana, "merges_done": merges, "memory_hidden": hidden}
    if num is not None:
        s["number_value"] = float(num)
        s["number_active"] = True
    if color is not None:
        r, g, b = color
        s["color_r"] = r
        s["color_g"] = g
        s["color_b"] = b
    if shape is not None:
        s["shape_index"] = shape
    if word is not None:
        s["word_value"] = word
    return s


def _empty_slot():
    return {"occupied": False}


def _make_obs():
    return {"action_mask": np.ones(38, dtype=np.int8)}


def _make_info(*, mana: float = 200, slots=None):
    return {
        "raw_state": {
            "mana": mana,
            "mana_max": mana,
            "action_count": 0,
            "max_steps": 100,
            "slots": slots if slots is not None else [],
            "valid_actions": [0, 37],
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# Pure encoders
# ──────────────────────────────────────────────────────────────────────────────


class TestCompactSlotEncoder:
    def test_empty_slot_is_dot(self):
        assert _compact_slot(_empty_slot()) == "."

    def test_number_only_card(self):
        s = _slot_card(num=2, mana=15, merges=1)
        assert _compact_slot(s) == "+2,m15,x1"

    def test_negative_number(self):
        s = _slot_card(num=-3, mana=9, merges=0)
        # sign must always be present so the model never has to guess
        assert _compact_slot(s) == "-3,m9,x0"

    def test_zero_number_active(self):
        s = _slot_card(num=0, mana=18, merges=2)
        # number_active=True forces emission even when value is 0
        assert _compact_slot(s) == "+0,m18,x2"

    def test_fractional_number(self):
        s = _slot_card(num=0.5, mana=9, merges=0)
        out = _compact_slot(s)
        assert "+0.5" in out
        assert out.endswith(",m9,x0")

    def test_color_red(self):
        s = _slot_card(color=(1, 0, 0), mana=9, merges=0)
        assert _compact_slot(s) == "R,m9,x0"

    def test_color_yellow(self):
        s = _slot_card(color=(1, 1, 0), mana=9, merges=0)
        assert _compact_slot(s) == "Y,m9,x0"

    def test_number_and_color(self):
        s = _slot_card(num=2, color=(0, 1, 0), mana=15, merges=1)
        assert _compact_slot(s) == "+2,G,m15,x1"

    def test_shape_index(self):
        s = _slot_card(shape=5, mana=9, merges=0)
        assert _compact_slot(s) == "s5,m9,x0"

    def test_word_card(self):
        s = _slot_card(word="cat", mana=9, merges=0)
        assert _compact_slot(s) == "[cat],m9,x0"

    def test_multidim_card(self):
        s = _slot_card(num=2, color=(0, 0, 1), shape=3, mana=27, merges=2)
        assert _compact_slot(s) == "+2,B,s3,m27,x2"

    def test_hidden_card(self):
        s = {"occupied": True, "memory_hidden": True, "card_mana": 15, "merges_done": 1}
        assert _compact_slot(s) == "?,m15,x1"

    def test_hidden_overrides_visible_dimensions(self):
        # Even if the dim values are present, memory_hidden=True must mask them
        s = _slot_card(num=2, color=(1, 0, 0), mana=15, merges=1, hidden=True)
        out = _compact_slot(s)
        assert out.startswith("?,")
        assert "+2" not in out
        assert "R" not in out


class TestCompactSlotsRow:
    def test_six_positions_with_pipe_separator(self):
        slots = [
            _slot_card(num=1, mana=9),                # new
            _slot_card(num=2, color=(1, 0, 0), mana=15, merges=1),  # s1
            _empty_slot(),                            # s2
            _empty_slot(),                            # s3
            _empty_slot(),                            # s4
            _empty_slot(),                            # s5
        ]
        row = _compact_slots_row(slots)
        cells = row.split("|")
        assert len(cells) == 6
        assert cells[0] == "+1,m9,x0"
        assert cells[1] == "+2,R,m15,x1"
        assert cells[2:] == [".", ".", ".", "."]

    def test_extra_trailing_slot_ignored(self):
        # The bridge sometimes appends a "sell" pseudo-slot at index 6
        slots = [_empty_slot()] * 7
        row = _compact_slots_row(slots)
        assert row == "|".join(["."] * 6)

    def test_short_slot_array_padded_with_dots(self):
        row = _compact_slots_row([])
        assert row == "|".join(["."] * 6)

        row2 = _compact_slots_row([_slot_card(num=1, mana=9)])
        cells = row2.split("|")
        assert len(cells) == 6
        assert cells[0] == "+1,m9,x0"
        assert cells[1:] == ["."] * 5


class TestAnnotateAction:
    @pytest.mark.parametrize("action,expected", [
        (0,  "a0:draw"),
        (37, "a37:wait"),
        (1,  "a1:new>s1"),    # src=new, dst=s1
        (5,  "a5:new>s5"),    # src=new, dst=s5
        (6,  "a6:s1>s1"),     # src=s1, dst=s1 (illegal in practice; encoder is lossless)
        (10, "a10:s1>s5"),
        (11, "a11:s2>s1"),
        (30, "a30:s5>s5"),
        (31, "a31:sell(new)"),
        (32, "a32:sell(s1)"),
        (36, "a36:sell(s5)"),
    ])
    def test_action_annotations(self, action, expected):
        assert _annotate_action(action) == expected


class TestFormatTrailEntry:
    def test_basic_entry(self):
        slots = [
            _slot_card(num=1, mana=9),
            _empty_slot(),
            _empty_slot(),
            _empty_slot(),
            _empty_slot(),
            _empty_slot(),
        ]
        line = format_trail_entry(
            step_idx=0, slots_before=slots, action=2,
            mana_before=200.0, mana_after=215.0,
        )
        assert line.startswith("t0 ")
        assert "[+1,m9,x0|.|.|.|.|.]" in line
        assert "a2:new>s2" in line
        assert "m215(+15)" in line

    def test_negative_delta(self):
        slots = [_empty_slot()] * 6
        line = format_trail_entry(
            step_idx=12, slots_before=slots, action=0,
            mana_before=180.0, mana_after=170.0,
        )
        assert "t12 " in line
        assert "m170(-10)" in line


# ──────────────────────────────────────────────────────────────────────────────
# build_system_prompt + history legend
# ──────────────────────────────────────────────────────────────────────────────


class TestHistoryLegend:
    def test_legend_omitted_by_default(self):
        out = build_system_prompt({"number": "add"})
        assert "HISTORY FORMAT" not in out
        assert "PAST STEPS" not in out

    def test_legend_included_when_requested(self):
        out = build_system_prompt({"number": "add"}, include_history_legend=True)
        assert "HISTORY FORMAT" in out
        # Documents the action annotation alphabet
        assert "a0:draw" in out
        assert "a37:wait" in out
        assert "sell(src)" in out
        # Documents slot cell format
        assert "[new|s1|s2|s3|s4|s5]" in out
        # Color legend
        assert "Red" in out and "Green" in out and "Blue" in out

    def test_legend_with_registry_prompt(self):
        out = build_system_prompt(
            {"number": "add"}, prompt=get_default_prompt(),
            include_history_legend=True,
        )
        assert "HISTORY FORMAT" in out
        # Original core rules still present
        assert "YEDI" in out


# ──────────────────────────────────────────────────────────────────────────────
# LLMAgent in compact mode
# ──────────────────────────────────────────────────────────────────────────────


class TestCompactLLMAgent:
    def test_compact_mode_uses_one_shot_call(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        agent.act(_make_obs(), _make_info())
        # Compact mode is one-shot like stateless: a single user message,
        # not an accumulating message list
        assert len(prov.calls[0]["messages"]) == 1
        assert prov.calls[0]["messages"][0]["role"] == "user"
        # The conversation history list must stay empty in compact mode
        assert agent._messages == []

    def test_compact_mode_system_prompt_has_legend(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        assert "HISTORY FORMAT" in agent._system_prompt

    def test_first_step_has_no_trail(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        agent.act(_make_obs(), _make_info(mana=200))
        text = _user_text(prov.calls[-1])
        assert "(none yet)" in text
        assert "CURRENT STATE:" in text

    def test_trail_grows_across_steps(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")

        # Step 1: act() with mana=200, then on_step_result() with mana=215
        agent.act(_make_obs(), _make_info(mana=200, slots=[
            _slot_card(num=1, mana=9), _empty_slot(), _empty_slot(),
            _empty_slot(), _empty_slot(), _empty_slot(),
        ]))
        agent.on_step_result(0, +0.15, False, _make_info(mana=215))

        # Step 2: act() — must contain the finalized trail line for step 0
        agent.act(_make_obs(), _make_info(mana=215))
        text = _user_text(prov.calls[-1])
        assert "PAST STEPS" in text
        assert "(none yet)" not in text
        assert "t0 " in text
        assert "a0:draw" in text
        assert "m215(+15)" in text
        assert "CURRENT STATE:" in text

    def test_trail_records_negative_delta(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        agent.act(_make_obs(), _make_info(mana=200))
        agent.on_step_result(0, -0.10, False, _make_info(mana=190))
        agent.act(_make_obs(), _make_info(mana=190))
        text = _user_text(prov.calls[-1])
        assert "m190(-10)" in text

    def test_pending_cleared_after_finalize(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        agent.act(_make_obs(), _make_info(mana=200))
        assert agent._pending_trail is not None
        agent.on_step_result(0, 0.0, False, _make_info(mana=200))
        assert agent._pending_trail is None
        assert len(agent._compact_trail) == 1

    def test_reset_clears_trail_and_pending(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        agent.act(_make_obs(), _make_info(mana=200))
        agent.on_step_result(0, 0.0, False, _make_info(mana=210))
        agent.act(_make_obs(), _make_info(mana=210))
        assert len(agent._compact_trail) == 1
        assert agent._pending_trail is not None

        agent.reset()
        assert agent._compact_trail == []
        assert agent._pending_trail is None
        assert agent._exchange_step_counter == 0

    def test_provider_error_still_records_pending(self):
        """If the provider crashes, the fallback action must still appear in
        the trail so the next step's prompt isn't missing a row."""
        class BoomProvider(StubProvider):
            def complete(self, messages, system=None, should_cancel=None):
                raise RuntimeError("network down")

        prov = BoomProvider()
        mask = np.zeros(38, dtype=np.int8)
        mask[3] = 1
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        action = agent.act({"action_mask": mask}, _make_info(mana=200))
        assert action == 3  # fallback
        assert agent._pending_trail is not None
        assert agent._pending_trail["action"] == 3

        agent.on_step_result(action, -0.05, False, _make_info(mana=195))
        assert len(agent._compact_trail) == 1
        assert "a3:new>s3" in agent._compact_trail[0]
        assert "m195(-5)" in agent._compact_trail[0]

    def test_trail_capped_at_max_history(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        # Push past the cap
        for i in range(MAX_HISTORY_TURNS + 20):
            agent.act(_make_obs(), _make_info(mana=200 + i))
            agent.on_step_result(0, 0.0, False, _make_info(mana=200 + i + 1))
        # Trail must be bounded
        assert len(agent._compact_trail) <= MAX_HISTORY_TURNS
        # The first entry is preserved (special case in the trim logic) so
        # the model retains its opening context
        assert "t0 " in agent._compact_trail[0]

    def test_set_game_modes_keeps_legend(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov, prompt=get_default_prompt(),
            mode="compact", game_modes={"number": "add"},
        )
        assert "HISTORY FORMAT" in agent._system_prompt
        agent.set_game_modes({"number": "multiply"})
        assert "HISTORY FORMAT" in agent._system_prompt
        assert "MULTIPLY" in agent._system_prompt.upper()

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError, match="mode must be one of"):
            LLMAgent(
                provider=StubProvider(),
                prompt=get_default_prompt(),
                mode="bogus",
            )

    def test_default_name_includes_c_suffix(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="compact")
        assert agent.name.startswith("llm-meta-c-")

    def test_default_name_vision_compact(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov, prompt=get_default_prompt(),
            mode="compact", use_screenshot=True,
        )
        assert agent.name.startswith("llm-vision-c-")


def _user_text(call: dict) -> str:
    """Extract the text content block sent to the provider in a single call."""
    content = call["messages"][-1]["content"]
    if isinstance(content, list):
        for block in content:
            if block.get("type") == "text":
                return block["text"]
        raise AssertionError(f"no text block in content: {content!r}")
    return content
