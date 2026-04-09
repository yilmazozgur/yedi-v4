"""Tests for prompt assembly + LLMAgent's interaction with the provider layer.

We never call a real LLM here — providers are mocked or replaced with a stub.
"""

from __future__ import annotations

import numpy as np
import pytest

from yedi_benchmark.agents.llm_agent import (
    CORE_RULES,
    DIMENSION_RULES,
    LLMAgent,
    _build_sell_hint,
    build_system_prompt,
    describe_state,
    format_trail_entry,
)
from yedi_benchmark.providers.base import LLMProvider
from yedi_benchmark.registries.default_prompt import get_default_prompt
from yedi_benchmark.registries.models import Prompt


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


class StubProvider(LLMProvider):
    """In-memory provider that records every call and returns canned text."""

    def __init__(self, reply: str = "0", model: str = "stub-model", max_tokens: int = 64):
        super().__init__(model=model, max_tokens=max_tokens, supports_vision=True)
        self.reply = reply
        self.calls: list[dict] = []

    def complete(self, messages, system=None, should_cancel=None):
        self.calls.append({
            "messages": messages, "system": system, "should_cancel": should_cancel,
        })
        return self.reply


def _make_obs():
    return {"action_mask": np.ones(38, dtype=np.int8)}


def _make_info():
    return {
        "raw_state": {
            "mana": 200,
            "mana_max": 200,
            "action_count": 0,
            "max_steps": 100,
            "slots": [],
            "mode_number": "add",
            "valid_actions": [0, 37],
        }
    }


# ──────────────────────────────────────────────────────────────────────────────
# build_system_prompt
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildSystemPrompt:
    def test_legacy_path_includes_core_and_dimension(self):
        out = build_system_prompt({"number": "add"})
        assert "YEDI" in out
        assert "MATH — ADD MODE" in out
        assert "RESPONSE FORMAT" in out

    def test_legacy_path_no_active_modes(self):
        out = build_system_prompt({})
        assert "No specific dimension rules" in out

    def test_legacy_path_skips_empty_mode_values(self):
        out = build_system_prompt({"number": "add", "color": ""})
        assert "MATH — ADD MODE" in out
        assert "VISUAL" not in out  # empty mode value not picked up

    def test_registry_path_uses_prompt_object(self):
        custom = Prompt(
            name="Custom",
            core_rules="THESE ARE CUSTOM CORE RULES",
            dimension_rules={"number:add": "Custom add rule.", "color:add": "Custom color rule."},
        )
        out = build_system_prompt({"number": "add", "color": "add"}, prompt=custom)
        assert "THESE ARE CUSTOM CORE RULES" in out
        assert "Custom add rule." in out
        assert "Custom color rule." in out
        # Legacy constants should NOT leak in
        assert "MATH — ADD MODE" not in out

    def test_registry_path_missing_rule_falls_through(self):
        custom = Prompt(
            name="Sparse",
            core_rules="core",
            dimension_rules={"number:add": "only one rule"},
        )
        # color:add is not in the dict — should not error, just skip
        out = build_system_prompt({"number": "add", "color": "add"}, prompt=custom)
        assert "only one rule" in out

    def test_default_prompt_matches_legacy_assembly(self):
        """The Prompt registry seeds from llm_agent's constants. The two paths
        must produce identical strings for any active modes."""
        prompt = get_default_prompt()

        for modes in [
            {"number": "add"},
            {"number": "subtract", "color": "add"},
            {"shape": "triangle", "memory": "every action"},
            {"word": "scrabble"},
            {"number": "add", "color": "add", "shape": "triangle", "memory": "every action"},
        ]:
            legacy = build_system_prompt(modes)
            registry = build_system_prompt(modes, prompt=prompt)
            assert legacy == registry, f"diverged for modes={modes}"

    def test_default_prompt_covers_all_dimension_rules(self):
        """Every (field, mode) tuple in DIMENSION_RULES must round-trip into the
        flat 'field:mode' key format and back."""
        prompt = get_default_prompt()
        assert len(prompt.dimension_rules) == len(DIMENSION_RULES)
        for (field, mode), rule in DIMENSION_RULES.items():
            assert prompt.dimension_rules[f"{field}:{mode}"] == rule


# ──────────────────────────────────────────────────────────────────────────────
# describe_state
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribeState:
    def test_empty_state(self):
        assert "not started" in describe_state({}).lower()

    def test_basic_summary(self):
        out = describe_state({
            "mana": 250, "mana_max": 300,
            "action_count": 5, "max_steps": 100,
            "slots": [
                {"occupied": True, "card_mana": 9, "merges_done": 0, "number_value": 3, "number_active": True},
                {"occupied": False},
            ],
            "valid_actions": [0, 37],
        })
        assert "Mana: 250" in out
        assert "Best: 300" in out
        assert "Step: 5/100" in out
        assert "Num=3" in out
        assert "Empty" in out

    def test_hidden_card(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "action_count": 0, "max_steps": 100,
            "slots": [
                {"occupied": True, "card_mana": 9, "merges_done": 0, "memory_hidden": True},
            ],
        })
        assert "HIDDEN" in out
        assert "Num=" not in out

    def test_game_over_marker(self):
        out = describe_state({
            "mana": 0, "mana_max": 200,
            "slots": [],
            "game_over": True,
        })
        assert "GAME OVER" in out

    # ──────────────────────────────────────────────────────────────────
    # merge_previews block — pre-computed per-merge gain tiers from the
    # bridge. Off by default (canonical benchmark) so the LLM has to score
    # merges from the slot dump. Flipping show_merge_previews=True enables
    # the assisted ablation that surfaces the bridge-side gains directly.
    # ──────────────────────────────────────────────────────────────────
    def test_merge_previews_renders_active_dims_only(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "mode_color": "",         # inactive — must NOT appear in output
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 2, "color_gain": -1,
                    "shape_gain": 0, "word_gain": 0,
                },
                {
                    "source": "new", "target": "2", "action": 2,
                    "number_gain": 3, "color_gain": -1,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        assert "Merge previews" in out
        # New format: "a1   new→1: Number GREAT ×2.0"
        assert "new→1" in out and "Number GREAT" in out and "×2.0" in out
        assert "new→2" in out and "Number PERFECT" in out and "×2.5" in out
        # Action IDs lead each row
        assert "a1" in out
        assert "a2" in out
        # color is inactive, must not leak
        assert "Color" not in out

    def test_merge_previews_multi_dim(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "mode_color": "add",
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 2, "color_gain": 1,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        # Both active dims appear in tier-word + multiplier form
        assert "Number GREAT ×2.0" in out
        assert "Color GOOD ×1.5" in out

    def test_merge_previews_omitted_when_empty(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "merge_previews": [],
        }, show_merge_previews=True)
        assert "Merge previews" not in out

    def test_merge_previews_omitted_when_no_active_dims(self):
        # Defensive: if for some reason no dim is active, the previews block
        # would be all zeros — skip it instead of dumping noise.
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 2, "color_gain": 0,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        assert "Merge previews" not in out

    def test_merge_previews_negative_gain_renders_as_bad_tier(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": -1, "color_gain": 0,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        # New format renders -1 as "BAD ×0.9" instead of bare "Num=-1".
        # The slot-value notation ("Num=-1.0") is what the old format
        # collided with — small models read it as a card value. Tier
        # words eliminate that overlap.
        assert "Number BAD ×0.9" in out
        assert "Num=-1" not in out

    def test_merge_previews_neutral_tier_renders_one_x(self):
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 0, "color_gain": 0,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        assert "Number neutral ×1.0" in out

    def test_merge_previews_unknown_tier_falls_through(self):
        # Defensive: if the bridge ever ships a tier outside {-1..3} we
        # should not crash — render it as "tier+N" with a "?" multiplier.
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 7, "color_gain": 0,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }, show_merge_previews=True)
        assert "tier+7" in out
        assert "×?" in out

    # ──────────────────────────────────────────────────────────────────
    # show_merge_previews gating
    # ──────────────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────
    # hide_perceptual_attrs — vision-mode leak guard. When the agent is
    # running with a screenshot, the text dump must NOT expose per-slot
    # card attributes (number/color/shape/word), otherwise the model can
    # solve the visual perception test from the text alone.
    # ──────────────────────────────────────────────────────────────────
    def test_vision_strips_per_slot_attributes(self):
        raw = {
            "mana": 200, "mana_max": 200,
            "action_count": 0, "max_steps": 100,
            "slots": [
                {
                    "occupied": True, "card_mana": 9, "merges_done": 1,
                    "number_value": 3, "number_active": True,
                    "color_r": 1.0, "color_g": 0.0, "color_b": 0.0,
                    "shape_index": 2,
                    "word_value": "apple",
                },
                {"occupied": False},
            ],
            "valid_actions": [0, 37],
        }
        out = describe_state(raw, hide_perceptual_attrs=True)
        # HUD-level fields must still be present
        assert "Mana: 200" in out
        assert "Mana=9" in out
        assert "Merges=1" in out
        # The "see screenshot" marker should appear for the occupied slot
        assert "see screenshot" in out
        # But every per-dim token must be stripped
        assert "Num=" not in out
        assert "Color=" not in out
        assert "Shape=" not in out
        assert "Word=" not in out
        # And the empty slot must still render
        assert "Empty" in out

    def test_vision_keeps_hidden_marker(self):
        """Hidden cards must still say HIDDEN even in vision mode — the
        screenshot won't show the value either."""
        out = describe_state({
            "mana": 200, "mana_max": 200,
            "slots": [
                {"occupied": True, "card_mana": 9, "merges_done": 0, "memory_hidden": True},
            ],
        }, hide_perceptual_attrs=True)
        assert "HIDDEN" in out
        assert "Num=" not in out

    def test_metadata_mode_still_shows_attributes(self):
        """Guard against regressing the default path — metadata-mode agents
        depend on the per-dim tokens."""
        raw = {
            "mana": 200, "mana_max": 200,
            "slots": [
                {"occupied": True, "card_mana": 9, "merges_done": 0,
                 "number_value": 3, "number_active": True},
            ],
            "valid_actions": [0, 37],
        }
        out = describe_state(raw)  # default hide_perceptual_attrs=False
        assert "Num=3" in out

    def test_merge_previews_omitted_by_default(self):
        # Default canonical-benchmark behaviour: even with a fully-populated
        # previews block and active dims, nothing is rendered unless the
        # caller opts in. This is the "no leak" guarantee — the LLM is
        # graded on its own merge-scoring ability.
        raw = {
            "mana": 200, "mana_max": 200,
            "slots": [{"occupied": False}],
            "mode_number": "add",
            "merge_previews": [
                {
                    "source": "new", "target": "1", "action": 1,
                    "number_gain": 3, "color_gain": 0,
                    "shape_gain": 0, "word_gain": 0,
                },
            ],
        }
        # No flag → omitted
        assert "Merge previews" not in describe_state(raw)
        # Flag explicitly false → omitted
        assert "Merge previews" not in describe_state(raw, show_merge_previews=False)
        # Flag true → rendered
        assert "Merge previews" in describe_state(raw, show_merge_previews=True)


# ──────────────────────────────────────────────────────────────────────────────
# _build_sell_hint — discipline check surfaced in describe_state. Lifts the
# greedy agent's "should I sell now?" arithmetic into the prompt so small
# models stop liquidating mana=9 cards that cannot raise the score.
# ──────────────────────────────────────────────────────────────────────────────


def _slot(occupied=False, card_mana=0, merges=0, **extra):
    """Compact slot factory for sell-hint tests."""
    s = {"occupied": occupied, "card_mana": card_mana, "merges_done": merges}
    s.update(extra)
    return s


class TestSellHint:
    def test_no_built_slots_returns_empty(self):
        # Index 0 = new, 6 = sell. Neither counts as a sell candidate.
        slots = [
            _slot(occupied=True, card_mana=11),  # new — ignored
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        assert _build_sell_hint(slots, mana=180, mana_max=200) == ""

    def test_selling_now_would_beat_best(self):
        slots = [
            _slot(occupied=False),                            # new
            _slot(occupied=True, card_mana=72, merges=2),     # build 1
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        out = _build_sell_hint(slots, mana=190, mana_max=200)
        assert "slot 1" in out
        assert "+72" in out
        assert "2/3 merges" in out
        assert "action 32" in out
        # 190 + 72 = 262 > 200 → should encourage selling
        assert "raise Best" in out
        assert "262" in out

    def test_selling_now_short_of_best_warns(self):
        slots = [
            _slot(occupied=False),                            # new
            _slot(occupied=True, card_mana=18, merges=1),     # build 1
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        out = _build_sell_hint(slots, mana=120, mana_max=200)
        # 120 + 18 = 138 < 200 → discourage premature selling
        assert "138" in out
        assert "short by 62" in out
        assert "keep merging" in out

    def test_maxed_slot_annotated(self):
        slots = [
            _slot(occupied=False),                             # new
            _slot(occupied=False),
            _slot(occupied=True, card_mana=50, merges=3),      # build 2 — MAXED
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        out = _build_sell_hint(slots, mana=200, mana_max=200)
        assert "slot 2" in out
        assert "MAXED" in out
        assert "3/3 merges" in out
        assert "action 33" in out

    def test_picks_highest_mana_when_multiple_built(self):
        slots = [
            _slot(occupied=False),                             # new
            _slot(occupied=True, card_mana=20, merges=1),      # build 1
            _slot(occupied=True, card_mana=80, merges=2),      # build 2 — winner
            _slot(occupied=True, card_mana=15, merges=0),      # build 3
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        out = _build_sell_hint(slots, mana=100, mana_max=300)
        assert "slot 2" in out
        assert "+80" in out
        assert "action 33" in out  # 31 + 2

    def test_zero_best_falls_back_to_basic_hint(self):
        # Early-game / unknown best: still emit the basic candidate line
        # but skip the bank-vs-best comparison.
        slots = [
            _slot(occupied=False),                             # new
            _slot(occupied=True, card_mana=15, merges=0),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        out = _build_sell_hint(slots, mana=180, mana_max=0)
        assert "slot 1" in out
        assert "+15" in out
        assert "Bank would become 195" in out
        assert "raise Best" not in out
        assert "short by" not in out

    def test_handles_string_or_none_card_mana(self):
        # Defensive: bridge has been seen to ship integer-as-string in odd
        # serializer paths, and `None` shows up during rapid resets.
        slots = [
            _slot(occupied=False),
            {"occupied": True, "card_mana": "30", "merges_done": "1"},
            {"occupied": True, "card_mana": None, "merges_done": None},
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
            _slot(occupied=False),
        ]
        # Should not raise; should pick slot 1 (card_mana=30 > None→0)
        out = _build_sell_hint(slots, mana=100, mana_max=200)
        assert "slot 1" in out
        assert "+30" in out

    def test_describe_state_includes_hint_when_built_slot_exists(self):
        """Integration check: the hint actually surfaces in describe_state
        output. Without this we could regress the call site silently."""
        raw = {
            "mana": 190, "mana_max": 200,
            "action_count": 5, "max_steps": 100,
            "mode_number": "add",
            "slots": [
                _slot(occupied=False),                          # new
                _slot(occupied=True, card_mana=72, merges=2,
                      number_value=4.0, number_active=True),    # build 1
                _slot(occupied=False),
                _slot(occupied=False),
                _slot(occupied=False),
                _slot(occupied=False),
                _slot(occupied=False),
            ],
            "valid_actions": [0, 32, 37],
        }
        out = describe_state(raw)
        assert "Sell hint" in out
        assert "slot 1" in out
        assert "raise Best" in out

    def test_describe_state_skips_hint_with_no_built_slots(self):
        raw = {
            "mana": 200, "mana_max": 200,
            "action_count": 0, "max_steps": 100,
            "mode_number": "add",
            "slots": [_slot(occupied=False) for _ in range(7)],
            "valid_actions": [0, 37],
        }
        out = describe_state(raw)
        assert "Sell hint" not in out


# ──────────────────────────────────────────────────────────────────────────────
# LLMAgent end-to-end with stub provider
# ──────────────────────────────────────────────────────────────────────────────


class TestLLMAgent:
    def test_stateless_act_uses_provider(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov,
            prompt=get_default_prompt(),
            mode="stateless",
            game_modes={"number": "add"},
        )
        action = agent.act(_make_obs(), _make_info())
        assert action == 0
        assert len(prov.calls) == 1
        # System prompt should be set, not appended to messages list
        assert "YEDI" in prov.calls[0]["system"]
        assert prov.calls[0]["messages"][0]["role"] == "user"

    def test_conversational_appends_history(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov,
            prompt=get_default_prompt(),
            mode="conversational",
            game_modes={"number": "add"},
        )
        agent.act(_make_obs(), _make_info())
        agent.act(_make_obs(), _make_info())
        # Two user turns + two assistant replies = 4 messages
        assert len(agent._messages) == 4
        assert agent._messages[0]["role"] == "user"
        assert agent._messages[1]["role"] == "assistant"
        assert agent._messages[2]["role"] == "user"
        assert agent._messages[3]["role"] == "assistant"

    def test_reset_clears_history(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="conversational")
        agent.act(_make_obs(), _make_info())
        assert len(agent._messages) > 0
        agent.reset()
        assert agent._messages == []

    def test_vision_mode_emits_image_url_block(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov,
            prompt=get_default_prompt(),
            mode="stateless",
            use_screenshot=True,
            game_modes={"number": "add"},
        )
        info = _make_info()
        info["screenshot"] = np.zeros((4, 4, 3), dtype=np.uint8)
        agent.act(_make_obs(), info)
        content = prov.calls[0]["messages"][0]["content"]
        img_blocks = [b for b in content if b.get("type") == "image_url"]
        assert len(img_blocks) == 1
        url = img_blocks[0]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")
        # Old Anthropic 'image' block must NOT be present
        assert all(b.get("type") != "image" for b in content)

    def test_vision_mode_skips_when_no_screenshot(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov, prompt=get_default_prompt(),
            mode="stateless", use_screenshot=True,
        )
        agent.act(_make_obs(), _make_info())  # no 'screenshot' key
        content = prov.calls[0]["messages"][0]["content"]
        # Should still have the text block, just no image
        assert any(b.get("type") == "text" for b in content)
        assert all(b.get("type") != "image_url" for b in content)

    def test_parse_action_picks_first_valid_number(self):
        prov = StubProvider(reply="I think the best move is 7 or maybe 12")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        action = agent.act(_make_obs(), _make_info())
        assert action == 7

    def test_parse_action_falls_back_to_mask(self):
        prov = StubProvider(reply="42")  # 42 > action space
        mask = np.zeros(38, dtype=np.int8)
        mask[5] = 1
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        action = agent.act({"action_mask": mask}, _make_info())
        assert action == 5

    # ──────────────────────────────────────────────────────────────────
    # ACTION: <n> marker — the new preferred response format. The model
    # is now allowed to write a short reasoning line first; the parser
    # must lock onto the explicit marker so a stray "slot 3" mention in
    # the reasoning doesn't get picked as the action.
    # ──────────────────────────────────────────────────────────────────
    def test_parse_action_marker_basic(self):
        prov = StubProvider(reply="ACTION: 19")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        assert agent.act(_make_obs(), _make_info()) == 19

    def test_parse_action_marker_after_reasoning(self):
        prov = StubProvider(reply=(
            "Slot 3 has Num=2, new is Num=-2 → sum=0, ×2.0. Best option.\n"
            "ACTION: 19"
        ))
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        # If the parser ignored the marker it would pick 3 (slot 3) or 2 first.
        assert agent.act(_make_obs(), _make_info()) == 19

    def test_parse_action_marker_case_insensitive(self):
        prov = StubProvider(reply="some thinking...\naction: 7")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        assert agent.act(_make_obs(), _make_info()) == 7

    def test_parse_action_marker_invalid_falls_through(self):
        """If the marker names an invalid action ID, the parser must fall
        through to the last-line / whole-text / mask logic instead of
        returning the bad ID."""
        prov = StubProvider(reply="ACTION: 99\nactually 7 is better")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        # 99 is out of range so the parser falls through and finds 7 in the
        # last line.
        assert agent.act(_make_obs(), _make_info()) == 7

    def test_parse_action_last_line_preferred_over_prose(self):
        """No marker, but the answer is on the last line. The parser should
        prefer the last line over the first integer in earlier prose."""
        prov = StubProvider(reply=(
            "Looking at slot 3 and slot 4, sum would be 5 — bad.\n"
            "Better to merge new into slot 1.\n"
            "7"
        ))
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        # Without last-line preference the parser would have picked 3.
        assert agent.act(_make_obs(), _make_info()) == 7

    def test_provider_error_falls_back(self):
        class BoomProvider(StubProvider):
            def complete(self, messages, system=None, should_cancel=None):
                raise RuntimeError("network down")

        prov = BoomProvider()
        mask = np.zeros(38, dtype=np.int8)
        mask[3] = 1
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="stateless")
        action = agent.act({"action_mask": mask}, _make_info())
        assert action == 3  # fallback picked the only valid action

    def test_set_game_modes_rebuilds_prompt(self):
        prov = StubProvider(reply="0")
        agent = LLMAgent(
            provider=prov, prompt=get_default_prompt(),
            mode="stateless", game_modes={"number": "add"},
        )
        before = agent._system_prompt
        agent.set_game_modes({"number": "multiply"})
        after = agent._system_prompt
        assert before != after
        assert "MULTIPLY" in after.upper()

    def test_default_provider_built_when_none(self):
        """Legacy ctor: passing model= without a provider must construct one."""
        agent = LLMAgent(model="claude-sonnet-4-5", mode="stateless")
        from yedi_benchmark.providers.litellm_provider import LiteLLMProvider
        assert isinstance(agent.provider, LiteLLMProvider)
        assert agent.provider.model == "claude-sonnet-4-5"

    def test_history_truncation(self):
        from yedi_benchmark.agents.llm_agent import MAX_HISTORY_TURNS

        prov = StubProvider(reply="0")
        agent = LLMAgent(provider=prov, prompt=get_default_prompt(), mode="conversational")
        # Push past the truncation cap
        for _ in range(MAX_HISTORY_TURNS + 5):
            agent.act(_make_obs(), _make_info())
        # The trim runs after the user message is appended (cap = MAX*2), but
        # the assistant reply is appended afterwards, so steady-state max is
        # MAX_HISTORY_TURNS*2 + 1.
        assert len(agent._messages) <= MAX_HISTORY_TURNS * 2 + 1
        # The trim must have actually fired — without it the count would grow
        # unbounded to ~2*(MAX_HISTORY_TURNS+5).
        assert len(agent._messages) < 2 * (MAX_HISTORY_TURNS + 5)


# ──────────────────────────────────────────────────────────────────────────────
# Vision-mode leak guards
# ──────────────────────────────────────────────────────────────────────────────


class TestVisionLeakGuards:
    """End-to-end check that enabling ``use_screenshot=True`` on the agent
    produces a prompt whose text side carries NO card attributes — not in
    the system prompt legend, not in the current-state dump, and not in the
    compact-mode trail.
    """

    def _vision_slot(self):
        return {
            "occupied": True, "card_mana": 15, "merges_done": 1,
            "number_value": 3, "number_active": True,
            "color_r": 1.0, "color_g": 0.0, "color_b": 0.0,
            "shape_index": 2,
            "word_value": "apple",
        }

    def test_compact_trail_vision_strips_attributes(self):
        slots = [self._vision_slot(), {"occupied": False}]
        entry = format_trail_entry(
            step_idx=3,
            slots_before=slots,
            action=0,  # a0:draw — does not mention any slot, keeps assertions clean
            mana_before=200.0,
            mana_after=215.0,
            hide_perceptual_attrs=True,
        )
        # The vision-mode cell marker for an occupied slot
        assert "X,m15,x1" in entry
        # Isolate the cell row (between [ and ]) so the action annotation
        # doesn't false-positive our "no per-dim tokens" assertions.
        row = entry.split("[", 1)[1].split("]", 1)[0]
        assert ",R," not in row
        assert ",G," not in row
        assert ",B," not in row
        assert "+3" not in row
        assert "-3" not in row
        assert "s2" not in row
        assert "[apple]" not in row

    def test_compact_trail_metadata_still_has_attributes(self):
        """Sanity: the default (metadata) path must still emit per-dim tokens."""
        slots = [self._vision_slot(), {"occupied": False}]
        entry = format_trail_entry(
            step_idx=3,
            slots_before=slots,
            action=0,
            mana_before=200.0,
            mana_after=215.0,
        )
        row = entry.split("[", 1)[1].split("]", 1)[0]
        # Number and colour tokens should be present (we had a R=1.0 card)
        assert "+3" in row
        assert ",R," in row

    def test_compact_trail_vision_preserves_hidden_cells(self):
        """Memory-hidden cards keep their '?' marker regardless of mode."""
        slots = [
            {"occupied": True, "card_mana": 15, "merges_done": 0, "memory_hidden": True},
            {"occupied": False},
        ]
        entry = format_trail_entry(
            step_idx=0,
            slots_before=slots,
            action=0,
            mana_before=200.0,
            mana_after=205.0,
            hide_perceptual_attrs=True,
        )
        assert "?,m15,x0" in entry
        assert "X,m15" not in entry  # hidden marker takes precedence

    def test_build_system_prompt_selects_vision_legend(self):
        out = build_system_prompt(
            {"number": "add"},
            include_history_legend=True,
            vision_legend=True,
        )
        assert "HISTORY FORMAT (compact mode, vision)" in out
        assert "screenshot is your only source" in out
        # The metadata legend header must NOT be present.
        assert "HISTORY FORMAT (compact mode) ====" not in out

    def test_build_system_prompt_selects_metadata_legend_by_default(self):
        out = build_system_prompt(
            {"number": "add"},
            include_history_legend=True,
        )
        assert "HISTORY FORMAT (compact mode) ====" in out
        assert "vision" not in out.split("HISTORY FORMAT")[1].splitlines()[0]

    def test_llm_agent_vision_compact_no_attribute_leak(self):
        """End-to-end: a vision + compact LLMAgent's outgoing user text must
        contain zero per-dim tokens, and its system prompt must carry the
        vision legend."""
        prov = StubProvider(reply="ACTION: 0")
        agent = LLMAgent(
            provider=prov,
            prompt=get_default_prompt(),
            mode="compact",
            use_screenshot=True,
            game_modes={"number": "add", "color": "add", "shape": "triangle"},
        )

        info = {
            "raw_state": {
                "mana": 200, "mana_max": 200,
                "action_count": 0, "max_steps": 100,
                "slots": [
                    {
                        "occupied": True, "card_mana": 15, "merges_done": 1,
                        "number_value": 3, "number_active": True,
                        "color_r": 1.0, "color_g": 0.0, "color_b": 0.0,
                        "shape_index": 2, "word_value": "apple",
                    },
                    {"occupied": False},
                ],
                "mode_number": "add",
                "mode_color": "add",
                "mode_shape": "triangle",
                "valid_actions": [0, 37],
            },
            "screenshot": np.zeros((4, 4, 3), dtype=np.uint8),
        }
        agent.act(_make_obs(), info)

        # 1) System prompt: vision legend, not metadata legend
        system = prov.calls[0]["system"]
        assert "HISTORY FORMAT (compact mode, vision)" in system
        assert "HISTORY FORMAT (compact mode) ====" not in system

        # 2) User text block: no per-dim tokens
        content = prov.calls[0]["messages"][0]["content"]
        text_blocks = [b["text"] for b in content if b.get("type") == "text"]
        assert len(text_blocks) == 1
        text = text_blocks[0]
        assert "Num=" not in text
        assert "Color=" not in text
        assert "Shape=" not in text
        assert "Word=" not in text
        assert "see screenshot" in text

    def test_llm_agent_vision_trail_stays_stripped_after_step(self):
        """After on_step_result finalises a trail entry, the next act() call
        must still carry attribute-free trail cells — regression guard for
        threading use_screenshot into format_trail_entry."""
        prov = StubProvider(reply="ACTION: 0")
        agent = LLMAgent(
            provider=prov,
            prompt=get_default_prompt(),
            mode="compact",
            use_screenshot=True,
            game_modes={"number": "add", "color": "add"},
        )

        info1 = {
            "raw_state": {
                "mana": 200, "mana_max": 200,
                "slots": [
                    {
                        "occupied": True, "card_mana": 15, "merges_done": 1,
                        "number_value": 3, "number_active": True,
                        "color_r": 1.0, "color_g": 0.0, "color_b": 0.0,
                    },
                ],
                "mode_number": "add",
                "mode_color": "add",
                "valid_actions": [0, 37],
            },
            "screenshot": np.zeros((4, 4, 3), dtype=np.uint8),
        }
        agent.act(_make_obs(), info1)
        agent.on_step_result(
            action=0, reward=0.0, terminated=False,
            info={"raw_state": {"mana": 215, "mana_max": 215}},
        )

        # Second act pass — the trail should now contain one entry
        info2 = {
            "raw_state": dict(info1["raw_state"]),
            "screenshot": np.zeros((4, 4, 3), dtype=np.uint8),
        }
        agent.act(_make_obs(), info2)

        text = next(
            b["text"] for b in prov.calls[1]["messages"][0]["content"]
            if b.get("type") == "text"
        )
        assert "PAST STEPS" in text
        assert "X,m15,x1" in text      # attribute-stripped trail cell
        # And the per-dim tokens from the source slot must not leak anywhere
        assert "+3" not in text
        assert ",R," not in text
