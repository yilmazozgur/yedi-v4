"""Featurizer / dataset-export tests.

The BC trainer is downstream of this module, so drift here silently
corrupts training data. Pin:

  * Source classification from agent_name.
  * Deterministic word hashing (survives PYTHONHASHSEED changes).
  * Slot-vector layout parity with ``yedi_env._serialize_slots``.
  * Round-trip through ``export_dataset`` with a tiny synthetic log.
"""

from __future__ import annotations

import json

import numpy as np
import pyarrow.parquet as pq
import pytest

from yedi_benchmark.learning import (
    DIMENSIONS,
    DIMENSIONS_DIM,
    NUM_SLOTS,
    SLOT_FEATURE_DIM,
    WORD_HASH_DIM,
    classify_agent_source,
    featurize_episode,
    featurize_step,
    hash_word,
    parse_active_dimensions,
)
from yedi_benchmark.learning.export_dataset import SCHEMA, export
from yedi_benchmark.yedi_env import YediEnv


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


def _slot(**overrides) -> dict:
    base = {
        "occupied": False,
        "card_mana": 0.0,
        "merges_done": 0,
        "number_value": 0.0,
        "color_r": 0.0, "color_g": 0.0, "color_b": 0.0,
        "shape_index": 0,
        "word_value": "",
        "memory_hidden": False,
    }
    base.update(overrides)
    return base


def _sample_state() -> dict:
    slots = [_slot() for _ in range(NUM_SLOTS)]
    slots[0] = _slot(occupied=True, card_mana=9, number_value=3,
                     color_r=0.1, color_g=0.2, color_b=0.3,
                     shape_index=5, word_value="Apple", merges_done=1)
    slots[2] = _slot(occupied=True, card_mana=7, number_value=-2,
                     color_r=0.9, shape_index=2,
                     word_value="banana", memory_hidden=True)
    return {
        "mana": 180.0, "mana_max": 210.0,
        "timer_remaining": 12.0, "beat_phase": 0.42,
        "game_over": False,
        "config_key": "math-add",
        "valid_actions": [0, 1, 31],
        "slots": slots,
    }


def _sample_step(action: int = 1, reward: float = 0.1) -> dict:
    state = _sample_state()
    return {
        "type": "step", "step": 0, "action": action,
        "command": {"type": "move_card", "source": "new", "target": "1"},
        "observation": {
            "action_mask": [1 if i in state["valid_actions"] else 0 for i in range(37)],
        },
        "reward": reward, "terminated": False, "truncated": False,
        "raw_state": state,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Pure functions
# ──────────────────────────────────────────────────────────────────────────────


class TestClassifyAgentSource:
    @pytest.mark.parametrize("name,expected", [
        ("Human-1", "human"),
        ("human_alice", "human"),
        ("Greedy", "greedy"),
        ("greedy-v2", "greedy"),
        ("Random", "random"),
        ("Claude Opus 4.6", "llm"),
        ("gpt-4o-mini", "llm"),
        ("", "unknown"),
    ])
    def test_classifies(self, name, expected):
        assert classify_agent_source(name) == expected


class TestHashWord:
    def test_empty_returns_zero_vector(self):
        assert np.array_equal(hash_word(""), np.zeros(WORD_HASH_DIM, dtype=np.float32))
        assert np.array_equal(hash_word(None), np.zeros(WORD_HASH_DIM, dtype=np.float32))
        assert np.array_equal(hash_word("   "), np.zeros(WORD_HASH_DIM, dtype=np.float32))

    def test_one_hot_structure(self):
        v = hash_word("apple")
        assert v.shape == (WORD_HASH_DIM,)
        assert v.sum() == 1.0
        assert v.max() == 1.0

    def test_case_and_whitespace_insensitive(self):
        assert np.array_equal(hash_word("Apple"), hash_word("apple"))
        assert np.array_equal(hash_word("  apple  "), hash_word("apple"))

    def test_deterministic_across_calls(self):
        # md5 means this survives PYTHONHASHSEED changes, unlike hash().
        v1 = hash_word("banana")
        v2 = hash_word("banana")
        assert np.array_equal(v1, v2)

    def test_different_words_hash_differently(self):
        # Not a collision guarantee, just a smoke test that the bucket
        # isn't stuck on a single index for everything.
        buckets = {int(np.argmax(hash_word(w)))
                   for w in ["apple", "banana", "cherry", "dog", "elephant"]}
        assert len(buckets) >= 3


# ──────────────────────────────────────────────────────────────────────────────
# Slot layout parity with yedi_env
# ──────────────────────────────────────────────────────────────────────────────


class TestParseActiveDimensions:
    """The multi-hot dimension vector lets the model specialize per mode
    without having to infer it from board state every step."""

    def test_empty_or_none_is_all_zeros(self):
        assert np.array_equal(parse_active_dimensions(""), np.zeros(DIMENSIONS_DIM))
        assert np.array_equal(parse_active_dimensions(None), np.zeros(DIMENSIONS_DIM))

    def test_single_dimension_colon_separator(self):
        vec = parse_active_dimensions("math:add")
        assert vec[DIMENSIONS.index("math")] == 1.0
        assert vec.sum() == 1.0

    def test_single_dimension_hyphen_separator(self):
        # Fixtures historically use ``"math-add"``; live runtime emits
        # ``"math:add"``. Both must parse identically.
        vec = parse_active_dimensions("math-add")
        assert vec[DIMENSIONS.index("math")] == 1.0

    def test_multi_dimension_plus_joined(self):
        vec = parse_active_dimensions("math:add+memory:every action")
        assert vec[DIMENSIONS.index("math")] == 1.0
        assert vec[DIMENSIONS.index("memory")] == 1.0
        assert vec.sum() == 2.0

    def test_unknown_tokens_ignored(self):
        # Sub-mode names ("add", "gcd", "verbs") must not light up a bit.
        vec = parse_active_dimensions("math:add+verbal:verbs")
        expected = np.zeros(DIMENSIONS_DIM, dtype=np.float32)
        expected[DIMENSIONS.index("math")] = 1.0
        expected[DIMENSIONS.index("verbal")] = 1.0
        np.testing.assert_array_equal(vec, expected)


class TestSlotLayoutParity:
    """Featurizer slot layout must match yedi_env._serialize_slots so
    a BC model trained on Parquet rows works in the live environment
    without any re-indexing."""

    def test_matches_env_serialize_slots(self):
        state = _sample_state()
        env = YediEnv.__new__(YediEnv)  # skip __init__ (no bridge needed)
        env_slots = env._serialize_slots(state)  # shape (7, 11)

        row = featurize_step(_sample_step(), episode_id="e", agent_name="x",
                             agent_source="random")
        feat_slots = np.array(row["slots"], dtype=np.float32).reshape(
            NUM_SLOTS, SLOT_FEATURE_DIM)

        np.testing.assert_array_equal(env_slots, feat_slots)


# ──────────────────────────────────────────────────────────────────────────────
# Step-level featurization
# ──────────────────────────────────────────────────────────────────────────────


class TestFeaturizeStep:
    def test_returns_expected_shape(self):
        row = featurize_step(_sample_step(), episode_id="e1",
                             agent_name="Human-1", agent_source="human")
        assert len(row["slots"]) == NUM_SLOTS * SLOT_FEATURE_DIM
        assert len(row["word_hash"]) == NUM_SLOTS * WORD_HASH_DIM
        assert len(row["action_mask"]) == 37

    def test_word_hash_zeros_for_empty_slots(self):
        row = featurize_step(_sample_step(), episode_id="e", agent_name="x",
                             agent_source="random")
        word_hash = np.array(row["word_hash"]).reshape(NUM_SLOTS, WORD_HASH_DIM)
        # slot 1 is empty → zero vector. slot 0 has "Apple" → one-hot.
        assert word_hash[1].sum() == 0
        assert word_hash[0].sum() == 1

    def test_action_mask_roundtrip_from_obs(self):
        step = _sample_step()
        # observation mask wins over valid_actions derivation.
        step["observation"]["action_mask"][5] = 1
        row = featurize_step(step, episode_id="e", agent_name="x",
                             agent_source="random")
        assert row["action_mask"][5] == 1

    def test_missing_raw_state_returns_none(self):
        step = _sample_step()
        del step["raw_state"]
        assert featurize_step(step, episode_id="e", agent_name="x",
                              agent_source="random") is None


# ──────────────────────────────────────────────────────────────────────────────
# Episode-level iteration
# ──────────────────────────────────────────────────────────────────────────────


class TestFeaturizeEpisode:
    def test_shifts_action_onto_previous_state(self):
        """Rows pair step[k-1]'s pre-state with step[k]'s action, so
        an episode with N step records yields N-1 rows."""
        events = [
            {"type": "episode_start", "episode_id": "ep42",
             "agent_name": "Greedy", "config": {}},
            _sample_step(action=1),
            _sample_step(action=31),
            _sample_step(action=5),
            {"type": "episode_end", "total_steps": 3},
        ]
        rows = list(featurize_episode(events))
        assert len(rows) == 2  # N-1 pairs
        assert all(r["episode_id"] == "ep42" for r in rows)
        assert all(r["agent_source"] == "greedy" for r in rows)
        # First action (1) is dropped; labels come from steps 1..N-1.
        assert [r["action"] for r in rows] == [31, 5]

    def test_short_episodes_emit_nothing(self):
        events = [
            {"type": "episode_start", "episode_id": "ep1", "agent_name": "Random"},
            _sample_step(),  # single step — no pair possible
            {"type": "episode_end"},
        ]
        assert list(featurize_episode(events)) == []

    def test_skips_non_step_events(self):
        events = [
            {"type": "episode_start", "episode_id": "ep1", "agent_name": "Random"},
            {"type": "screenshot", "step": 0, "path": "/tmp/x.png"},
            _sample_step(),
            _sample_step(),
            {"type": "episode_end"},
        ]
        rows = list(featurize_episode(events))
        assert len(rows) == 1  # two steps → one pair


# ──────────────────────────────────────────────────────────────────────────────
# Export CLI / Parquet round-trip
# ──────────────────────────────────────────────────────────────────────────────


class TestExportDataset:
    def _write_episode(self, log_dir, ep_id, agent_name, n_steps):
        ep_dir = log_dir / f"episode_{ep_id}"
        ep_dir.mkdir()
        with (ep_dir / "events.jsonl").open("w") as f:
            f.write(json.dumps({"type": "episode_start",
                                "episode_id": ep_id,
                                "agent_name": agent_name,
                                "config": {}}) + "\n")
            for i in range(n_steps):
                step = _sample_step(action=(i % 37))
                step["step"] = i
                f.write(json.dumps(step) + "\n")
            f.write(json.dumps({"type": "episode_end",
                                "total_steps": n_steps}) + "\n")

    def test_round_trip_parquet(self, tmp_path):
        # Featurizer shifts action onto previous state, so an episode
        # with n steps yields n-1 rows.
        logs = tmp_path / "logs"
        logs.mkdir()
        self._write_episode(logs, "A", "Human-1", n_steps=4)  # 3 pairs
        self._write_episode(logs, "B", "Greedy", n_steps=3)   # 2 pairs
        out = tmp_path / "out" / "bc.parquet"

        summary = export(logs, out)
        assert summary["num_rows"] == 5
        assert summary["num_episodes"] == 2
        assert summary["episodes_by_source"] == {"human": 1, "greedy": 1}

        table = pq.read_table(out)
        assert table.schema.equals(SCHEMA)
        assert table.num_rows == 5
        by_source = table.column("agent_source").to_pylist()
        assert sorted(by_source) == ["greedy", "greedy", "human", "human", "human"]

    def test_source_filter(self, tmp_path):
        logs = tmp_path / "logs"
        logs.mkdir()
        self._write_episode(logs, "A", "Human-1", 3)  # 2 pairs
        self._write_episode(logs, "B", "Greedy", 3)   # 2 pairs
        out = tmp_path / "bc.parquet"

        summary = export(logs, out, sources={"human"})
        assert summary["num_rows"] == 2
        assert summary["skipped_filtered"] == 1
        table = pq.read_table(out)
        assert set(table.column("agent_source").to_pylist()) == {"human"}

    def test_empty_dir_raises(self, tmp_path):
        logs = tmp_path / "logs"
        logs.mkdir()
        with pytest.raises(SystemExit):
            export(logs, tmp_path / "bc.parquet")
