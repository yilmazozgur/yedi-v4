"""Unit tests for the in-memory LLM exchange trace store.

These cover the surface that the dashboard polls — record/snapshot/cursor
semantics, system-prompt storage, LRU eviction, and basic thread safety.
"""

from __future__ import annotations

import threading

import pytest

from yedi_benchmark.run_trace import (
    MAX_ENTRIES_PER_RUN,
    MAX_RUNS_IN_STORE,
    RunTrace,
    RunTraceStore,
    get_run_trace_store,
    reset_run_trace_store,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_run_trace_store()
    yield
    reset_run_trace_store()


def _record(t: RunTrace, n: int = 1, *, config: str = "easy_math_add"):
    ids = []
    for i in range(n):
        ids.append(t.record(
            config=config,
            episode=0,
            step=i,
            user_text=f"in {i}",
            response=f"out {i}",
            action=i % 37,
            latency_ms=12.5,
        ))
    return ids


# ──────────────────────────────────────────────────────────────────────────────
# RunTrace
# ──────────────────────────────────────────────────────────────────────────────


class TestRunTrace:
    def test_record_returns_monotonic_ids(self):
        t = RunTrace("run_x")
        ids = _record(t, 3)
        assert ids == [1, 2, 3]

    def test_snapshot_from_zero_returns_all(self):
        t = RunTrace("run_x")
        _record(t, 5)
        snap = t.snapshot(since_id=0)
        assert snap["run_id"] == "run_x"
        assert snap["cursor"] == 5
        assert len(snap["entries"]) == 5
        assert [e["id"] for e in snap["entries"]] == [1, 2, 3, 4, 5]

    def test_snapshot_with_cursor_returns_only_new(self):
        t = RunTrace("run_x")
        _record(t, 3)
        _record(t, 2)
        snap = t.snapshot(since_id=3)
        assert [e["id"] for e in snap["entries"]] == [4, 5]
        assert snap["cursor"] == 5

    def test_snapshot_at_current_cursor_is_empty(self):
        t = RunTrace("run_x")
        _record(t, 3)
        snap = t.snapshot(since_id=3)
        assert snap["entries"] == []
        assert snap["cursor"] == 3

    def test_entry_payload_shape(self):
        t = RunTrace("run_x")
        t.record(
            config="easy_math_add", episode=2, step=7,
            user_text="state goes here", response="action 12",
            action=12, latency_ms=88.0,
        )
        e = t.snapshot()["entries"][0]
        assert e["config"] == "easy_math_add"
        assert e["episode"] == 2
        assert e["step"] == 7
        assert e["user_text"] == "state goes here"
        assert e["response"] == "action 12"
        assert e["action"] == 12
        assert e["latency_ms"] == 88.0
        assert e["error"] is None
        assert "ts" in e
        assert "id" in e

    def test_record_error_path(self):
        t = RunTrace("run_x")
        t.record(
            config="easy_math_add", episode=0, step=0,
            user_text="state", response="(provider failed)",
            action=0, latency_ms=None, error="HTTP 500",
        )
        e = t.snapshot()["entries"][0]
        assert e["error"] == "HTTP 500"
        assert e["latency_ms"] is None

    def test_buffer_caps_at_max(self):
        t = RunTrace("run_x")
        _record(t, MAX_ENTRIES_PER_RUN + 50)
        snap = t.snapshot(since_id=0)
        # Cursor keeps counting, but entries are bounded by deque maxlen
        assert snap["cursor"] == MAX_ENTRIES_PER_RUN + 50
        assert len(snap["entries"]) == MAX_ENTRIES_PER_RUN
        # Oldest entries got dropped — first kept entry has id == 51
        assert snap["entries"][0]["id"] == 51

    def test_set_system_prompt_stored_per_config(self):
        t = RunTrace("run_x")
        t.set_system_prompt("easy_math_add", "you are math")
        t.set_system_prompt("easy_visual_color", "you are color")
        snap = t.snapshot()
        assert snap["system_prompts"] == {
            "easy_math_add": "you are math",
            "easy_visual_color": "you are color",
        }

    def test_set_system_prompt_overwrites(self):
        t = RunTrace("run_x")
        t.set_system_prompt("easy_math_add", "v1")
        t.set_system_prompt("easy_math_add", "v2")
        assert t.snapshot()["system_prompts"]["easy_math_add"] == "v2"

    def test_thread_safety_concurrent_records(self):
        t = RunTrace("run_x")

        def writer():
            for i in range(100):
                t.record(
                    config="c", episode=0, step=i,
                    user_text="x", response="y", action=0, latency_ms=1.0,
                )

        threads = [threading.Thread(target=writer) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        snap = t.snapshot()
        # 8 threads × 100 records each = 800 — well over the 500 cap
        assert snap["cursor"] == 800
        assert len(snap["entries"]) == MAX_ENTRIES_PER_RUN
        # Ids must be unique and monotonically increasing
        ids = [e["id"] for e in snap["entries"]]
        assert ids == sorted(ids)
        assert len(set(ids)) == len(ids)


# ──────────────────────────────────────────────────────────────────────────────
# RunTraceStore
# ──────────────────────────────────────────────────────────────────────────────


class TestRunTraceStore:
    def test_get_or_create_returns_same_instance(self):
        s = RunTraceStore()
        a = s.get_or_create("run_1")
        b = s.get_or_create("run_1")
        assert a is b

    def test_get_returns_none_for_unknown(self):
        s = RunTraceStore()
        assert s.get("run_unknown") is None

    def test_get_returns_existing(self):
        s = RunTraceStore()
        t = s.get_or_create("run_1")
        assert s.get("run_1") is t

    def test_drop_removes_trace(self):
        s = RunTraceStore()
        s.get_or_create("run_1")
        s.drop("run_1")
        assert s.get("run_1") is None

    def test_drop_unknown_is_noop(self):
        s = RunTraceStore()
        s.drop("run_nope")  # must not raise

    def test_lru_evicts_oldest_when_full(self):
        s = RunTraceStore()
        for i in range(MAX_RUNS_IN_STORE):
            s.get_or_create(f"run_{i}")
        # All present
        assert s.get("run_0") is not None
        assert s.get(f"run_{MAX_RUNS_IN_STORE - 1}") is not None

        # One more — oldest should drop out
        s.get_or_create("run_overflow")
        assert s.get("run_0") is None
        assert s.get("run_overflow") is not None
        assert s.get(f"run_{MAX_RUNS_IN_STORE - 1}") is not None

    def test_clear_removes_all(self):
        s = RunTraceStore()
        s.get_or_create("run_1")
        s.get_or_create("run_2")
        s.clear()
        assert s.get("run_1") is None
        assert s.get("run_2") is None


# ──────────────────────────────────────────────────────────────────────────────
# Singleton helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestRunTraceStoreSingleton:
    def test_get_returns_same_instance(self):
        a = get_run_trace_store()
        b = get_run_trace_store()
        assert a is b

    def test_reset_creates_fresh_instance(self):
        a = get_run_trace_store()
        a.get_or_create("run_x")
        reset_run_trace_store()
        b = get_run_trace_store()
        assert a is not b
        assert b.get("run_x") is None


# ──────────────────────────────────────────────────────────────────────────────
# Runner integration: which agents create a trace?
# ──────────────────────────────────────────────────────────────────────────────
#
# The dashboard's pollTrace() distinguishes "no trace exists at all"
# (available=false → "no LLM trace for this run") from "trace exists but
# no entries yet" (available=true → "Waiting for the model's first move…").
# If the runner creates an empty trace for non-LLM agents, the UI gets
# stuck on the "Waiting…" placeholder forever for random/greedy runs.
# These tests pin the contract that the runner only creates the trace
# for actual LLM agents.


import numpy as np

from yedi_benchmark import benchmark_runner
from yedi_benchmark.benchmark_runner import run_benchmark_with_registry
from yedi_benchmark.registries import AgentRegistry


class _StubEnv:
    """Minimal Gymnasium-compatible env stub: one step, then terminate."""

    def __init__(self, server_url=None, game_config=None, max_steps=None):
        self.game_config = game_config or {}

    def reset(self, seed=None, options=None):
        return self._obs(), self._info()

    def step(self, action):
        return self._obs(), 0.0, True, False, self._info()

    def close(self):
        pass

    @staticmethod
    def _obs():
        return {"action_mask": np.ones(37, dtype=np.int8)}

    @staticmethod
    def _info():
        return {"raw_state": {"mana": 100, "mana_max": 100}, "max_mana": 100}


class TestRunnerTraceCreation:
    def test_random_agent_does_not_create_trace(
        self, isolated_data_dir, isolated_runs_dir, monkeypatch
    ):
        """The bug: a random-agent run was creating an empty trace, which
        made the dashboard's poll loop see available=true with no entries
        and stay stuck on "Waiting for the model's first move…" forever.
        After the fix, no trace exists for non-LLM agents."""
        monkeypatch.setattr(benchmark_runner, "YediEnv", _StubEnv)
        monkeypatch.setattr(benchmark_runner, "YediVLMEnv", _StubEnv)
        reset_run_trace_store()

        random_id = AgentRegistry().get_by_name("Random").id
        result = run_benchmark_with_registry(
            agent_id=random_id,
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=1,
            max_steps=2,
        )

        # Run finished but no trace entry was ever created — the dashboard
        # endpoint will return available=false and the JS will swap the
        # placeholder for the "no LLM trace" message.
        assert get_run_trace_store().get(result.id) is None

    def test_greedy_agent_does_not_create_trace(
        self, isolated_data_dir, isolated_runs_dir, monkeypatch
    ):
        """Greedy is also a non-LLM agent — same contract as random."""
        monkeypatch.setattr(benchmark_runner, "YediEnv", _StubEnv)
        monkeypatch.setattr(benchmark_runner, "YediVLMEnv", _StubEnv)
        reset_run_trace_store()

        greedy_id = AgentRegistry().get_by_name("Greedy").id
        result = run_benchmark_with_registry(
            agent_id=greedy_id,
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=1,
            max_steps=2,
        )

        assert get_run_trace_store().get(result.id) is None
