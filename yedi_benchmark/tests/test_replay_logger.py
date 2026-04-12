"""Tests for ReplayLogger — per-episode events.jsonl + trace.jsonl."""

from __future__ import annotations

import json

import numpy as np
import pytest

from yedi_benchmark.replay_logger import ReplayLogger


def _read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


class TestEventLog:
    def test_start_creates_episode_dir_with_events_file(self, tmp_path):
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={"modes": {"number": "add"}}, agent_name="test-agent")
        try:
            assert rl.episode_dir is not None
            assert rl.episode_dir.is_dir()
            assert (rl.episode_dir / "events.jsonl").exists()
        finally:
            rl.end_episode()

    def test_log_step_records_fallback_reason(self, tmp_path):
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="a")
        obs = {"mana": np.array([100.0])}
        rl.log_step(
            action=7,
            command={"type": "move_card", "source": "1", "target": "2"},
            observation=obs,
            reward=-0.05,
            terminated=False,
            truncated=False,
            info={"max_mana": 100},
            fallback_reason="llm_error: network down",
        )
        rl.end_episode()

        events = _read_jsonl(rl.episode_dir / "events.jsonl")
        step_events = [e for e in events if e["type"] == "step"]
        assert len(step_events) == 1
        assert step_events[0]["fallback_reason"] == "llm_error: network down"
        assert step_events[0]["action"] == 7

    def test_log_step_without_fallback_is_none(self, tmp_path):
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="a")
        rl.log_step(
            action=0,
            command={"type": "draw_card"},
            observation={"mana": np.array([100.0])},
            reward=0.0,
            terminated=False,
            truncated=False,
            info={},
        )
        rl.end_episode()

        events = _read_jsonl(rl.episode_dir / "events.jsonl")
        step_events = [e for e in events if e["type"] == "step"]
        assert step_events[0]["fallback_reason"] is None


class TestTraceLog:
    def test_log_exchange_writes_trace_file(self, tmp_path):
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="a")
        rl.log_exchange(
            step_in_episode=0,
            user_text="state dump",
            response="ACTION: 0",
            action=0,
            latency_ms=123.4,
            error=None,
            system_prompt="you are playing yedi",
        )
        rl.end_episode()

        trace_path = rl.episode_dir / "trace.jsonl"
        assert trace_path.exists()
        entries = _read_jsonl(trace_path)
        # first entry is the system prompt header
        assert entries[0]["type"] == "system_prompt"
        assert entries[0]["system_prompt"] == "you are playing yedi"
        # second entry is the exchange
        assert entries[1]["type"] == "exchange"
        assert entries[1]["step_in_episode"] == 0
        assert entries[1]["action"] == 0
        assert entries[1]["latency_ms"] == 123.4
        assert entries[1]["error"] is None
        assert entries[1]["fallback_reason"] is None

    def test_log_exchange_error_marks_fallback(self, tmp_path):
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="a")
        rl.log_exchange(
            step_in_episode=0,
            user_text="s1",
            response="",
            action=0,
            latency_ms=5.0,
            error="boom",
            fallback_reason="llm_error: boom",
        )
        rl.end_episode()
        entries = _read_jsonl(rl.episode_dir / "trace.jsonl")
        exchange = [e for e in entries if e["type"] == "exchange"][0]
        assert exchange["error"] == "boom"
        assert exchange["fallback_reason"] == "llm_error: boom"

    def test_no_trace_file_if_no_exchange_logged(self, tmp_path):
        """Random/greedy episodes shouldn't leave an empty trace.jsonl behind."""
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="random")
        rl.log_step(
            action=0, command={"type": "draw_card"},
            observation={"mana": np.array([200.0])},
            reward=0.0, terminated=False, truncated=False, info={},
        )
        rl.end_episode()
        assert not (rl.episode_dir / "trace.jsonl").exists()

    def test_system_prompt_stamped_only_once(self, tmp_path):
        """Subsequent calls must not re-emit the system prompt header."""
        rl = ReplayLogger(log_dir=str(tmp_path))
        rl.start_episode(config={}, agent_name="a")
        for i in range(3):
            rl.log_exchange(
                step_in_episode=i,
                user_text=f"t{i}",
                response=str(i),
                action=i,
                latency_ms=1.0,
                error=None,
                system_prompt="header",
            )
        rl.end_episode()
        entries = _read_jsonl(rl.episode_dir / "trace.jsonl")
        headers = [e for e in entries if e["type"] == "system_prompt"]
        assert len(headers) == 1
