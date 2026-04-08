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
    build_system_prompt,
    describe_state,
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
        assert "new→1 a1: Num=+2" in out
        assert "new→2 a2: Num=+3" in out
        # color is inactive, must not leak
        assert "Col=" not in out

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
        # Both active dims in output, in tier-format with explicit sign
        assert "Num=+2" in out
        assert "Col=+1" in out

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

    def test_merge_previews_negative_gain_renders_with_sign(self):
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
        assert "Num=-1" in out

    # ──────────────────────────────────────────────────────────────────
    # show_merge_previews gating
    # ──────────────────────────────────────────────────────────────────
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
