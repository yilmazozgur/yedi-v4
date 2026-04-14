"""Schema parity between AI episodes and human-recorded episodes.

Downstream, a behavior-cloning trainer reads ``events.jsonl`` from both
AI runs (greedy, LLM, random) and human runs and treats them as one
training set. That only works if both paths write identical record
schemas. Drift here would surface as silent training-time
``KeyError``s — or worse, as a BC model that learned to ignore a field
humans stopped emitting.

These tests pin down the contract by:

  1. Invoking ``ReplayLogger.log_step`` with the arguments each runner
     actually passes, on a shared raw-state fixture, and diffing the
     resulting records key-by-key.
  2. Running ``_run_episode_human`` with a fake env and a mocked
     ``/api/agent/events`` endpoint to confirm the human runner still
     produces start/step/end records with the expected fields.

Any change to the per-step schema that isn't mirrored on both sides
will fail one of these assertions.
"""

from __future__ import annotations

import json
import threading
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from yedi_benchmark import benchmark_runner
from yedi_benchmark.agents.human_agent import HumanAgent
from yedi_benchmark.replay_logger import ReplayLogger
from yedi_benchmark.yedi_env import action_to_command


# ──────────────────────────────────────────────────────────────────────────────
# Shared fixture: a realistic post-action raw_state as the bridge emits it.
# ──────────────────────────────────────────────────────────────────────────────


def _sample_raw_state() -> dict:
    """One frame of SerializeGameState, trimmed to the fields both runners rely on."""
    return {
        "mana": 214.0,
        "mana_max": 214.0,
        "timer_remaining": 18.3,
        "beat_phase": 0.0,
        "action_count": 3,
        "game_over": False,
        "valid_actions": [0, 1, 31],
        "slots": [
            {"occupied": True, "card_mana": 15, "merges_done": 1,
             "number_value": 2, "color_r": 0.9, "color_g": 0.2, "color_b": 0.1,
             "shape_index": 2, "memory_hidden": False},
        ] + [{"occupied": False} for _ in range(6)],
        "merge_previews": [],
    }


def _sample_observation(raw: dict) -> dict:
    """Mimic YediEnv._state_to_obs on ``raw``. Doesn't need the real env."""
    mask = np.zeros(37, dtype=np.int8)
    for a in raw.get("valid_actions", []):
        if 0 <= a < 37:
            mask[a] = 1
    return {
        "mana":            np.array([raw["mana"]], dtype=np.float32),
        "mana_max":        np.array([raw["mana_max"]], dtype=np.float32),
        "timer_remaining": np.array([raw["timer_remaining"]], dtype=np.float32),
        "beat_phase":      np.array([raw["beat_phase"]], dtype=np.float32),
        "slots":           np.zeros((7, 11), dtype=np.float32),
        "action_mask":     mask,
    }


def _read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _step_record(events):
    steps = [e for e in events if e["type"] == "step"]
    assert len(steps) == 1, f"expected exactly one step record, got {len(steps)}"
    return steps[0]


# ──────────────────────────────────────────────────────────────────────────────
# Part 1: log_step signature parity between the two runner paths
# ──────────────────────────────────────────────────────────────────────────────


class TestLogStepParity:
    """The AI and human runners must hand log_step the same shape of args."""

    def _log_ai_step(self, tmp_path):
        """Mirror the arguments run_episode() passes to log_step."""
        raw = _sample_raw_state()
        obs = _sample_observation(raw)
        action = 1  # MOVE(new, 1)
        rl = ReplayLogger(log_dir=str(tmp_path / "ai"))
        rl.start_episode(config={"modes": {"number": "add"}}, agent_name="greedy")
        rl.log_step(
            action=action,
            command=action_to_command(action),
            observation=obs,
            reward=0.14,
            terminated=False,
            truncated=False,
            info={"raw_state": raw, "max_mana": raw["mana_max"],
                  "surplus": raw["mana_max"] - 200, "step": 1},
            fallback_reason=None,
            raw_state=raw,
        )
        rl.end_episode(raw)
        return _read_jsonl(rl.episode_dir / "events.jsonl")

    def _log_human_step(self, tmp_path):
        """Mirror the arguments _run_episode_human passes to log_step."""
        raw = _sample_raw_state()
        action = 1
        # The bridge rewrites "type":"state" -> "type":"human_step","action":N
        # before shipping the frame over the agent WS.
        human_ev = dict(raw, type="human_step", action=action)
        obs = _sample_observation(human_ev)
        rl = ReplayLogger(log_dir=str(tmp_path / "human"))
        rl.start_episode(config={"modes": {"number": "add"}}, agent_name="human")
        rl.log_step(
            action=action,
            command=action_to_command(action),
            observation=obs,
            reward=0.14,
            terminated=False,
            truncated=False,
            info={"raw_state": human_ev, "max_mana": human_ev["mana_max"],
                  "surplus": human_ev["mana_max"] - 200, "step": 1},
            fallback_reason=None,
            raw_state=human_ev,
        )
        rl.end_episode(human_ev)
        return _read_jsonl(rl.episode_dir / "events.jsonl")

    def test_top_level_step_keys_match(self, tmp_path):
        ai_step = _step_record(self._log_ai_step(tmp_path))
        hu_step = _step_record(self._log_human_step(tmp_path))
        assert set(ai_step.keys()) == set(hu_step.keys()), (
            f"top-level step schema drift:\n"
            f"  ai only: {set(ai_step) - set(hu_step)}\n"
            f"  human only: {set(hu_step) - set(ai_step)}"
        )

    def test_observation_keys_match(self, tmp_path):
        ai_step = _step_record(self._log_ai_step(tmp_path))
        hu_step = _step_record(self._log_human_step(tmp_path))
        assert set(ai_step["observation"].keys()) == set(hu_step["observation"].keys())

    def test_raw_state_shares_core_keys(self, tmp_path):
        """Human raw_state carries two bridge extras (``type`` and
        ``action``) because it's the human_step envelope. Every other key
        must match the AI frame."""
        ai_step = _step_record(self._log_ai_step(tmp_path))
        hu_step = _step_record(self._log_human_step(tmp_path))
        ai_keys = set(ai_step["raw_state"].keys())
        hu_keys = set(hu_step["raw_state"].keys())
        assert ai_keys.issubset(hu_keys), f"human raw_state dropped: {ai_keys - hu_keys}"
        assert hu_keys - ai_keys == {"type", "action"}, (
            f"unexpected human-only raw_state keys: {hu_keys - ai_keys - {'type', 'action'}}"
        )

    def test_episode_start_and_end_records_match(self, tmp_path):
        """``episode_start`` / ``episode_end`` envelopes must also agree."""
        ai_events = self._log_ai_step(tmp_path)
        hu_events = self._log_human_step(tmp_path)

        ai_start = [e for e in ai_events if e["type"] == "episode_start"][0]
        hu_start = [e for e in hu_events if e["type"] == "episode_start"][0]
        assert set(ai_start.keys()) == set(hu_start.keys())

        ai_end = [e for e in ai_events if e["type"] == "episode_end"][0]
        hu_end = [e for e in hu_events if e["type"] == "episode_end"][0]
        assert set(ai_end.keys()) == set(hu_end.keys())


# ──────────────────────────────────────────────────────────────────────────────
# Part 2: runner-level smoke test — _run_episode_human actually writes the log
# ──────────────────────────────────────────────────────────────────────────────


class _FakeHumanEnv:
    """Minimal YediEnv stand-in for _run_episode_human.

    Records the set_recording_mode commands sent to the bridge so the test
    can assert the recorder was turned on (and off) around the episode.
    """

    def __init__(self):
        self.server_url = "ws://localhost:9/ws/agent"
        self.game_config = {"modes": {"number": "add"}}
        self.recording_commands: list[dict] = []

    def reset(self, seed=None, options=None):
        raw = _sample_raw_state()
        return _sample_observation(raw), {"raw_state": raw}

    def _send_command(self, command, timeout=30.0):
        if command.get("type") == "set_recording_mode":
            self.recording_commands.append(dict(command))
        return {"type": "ack"}

    def _state_to_obs(self, state):
        return _sample_observation(state)

    def close(self):
        pass


def _make_events_response(payload):
    """urlopen context-manager double that returns ``payload`` as JSON bytes."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class TestRunnerLevelHumanRecording:
    def test_human_runner_logs_one_step_and_terminates(self, tmp_path):
        """Drive _run_episode_human with a scripted event stream and confirm
        the events.jsonl ends with a step + episode_end record."""
        env = _FakeHumanEnv()
        agent = HumanAgent(name="alice")
        rl = ReplayLogger(log_dir=str(tmp_path))

        # Scripted event stream from /api/agent/events:
        #   1st poll: one human_step
        #   2nd poll: human_game_over (terminates the loop)
        human_step = dict(_sample_raw_state(),
                          type="human_step", action=0,
                          mana=214.0, mana_max=214.0)
        game_over = {"type": "human_game_over"}

        responses = [
            _make_events_response([]),             # initial drain-before-start
            _make_events_response([human_step]),   # record one step
            _make_events_response([game_over]),    # terminate
        ]
        with patch("urllib.request.urlopen", side_effect=responses):
            result = benchmark_runner._run_episode_human(
                env, agent, rl, max_steps=50, poll_interval=0.0,
            )

        events = _read_jsonl(rl.episode_dir / "events.jsonl")
        types = [e["type"] for e in events]
        assert types[0] == "episode_start"
        assert types[-1] == "episode_end"
        step_records = [e for e in events if e["type"] == "step"]
        assert len(step_records) == 1
        assert step_records[0]["action"] == 0
        assert step_records[0]["command"] == {"type": "draw_card"}
        assert result["steps"] == 1
        assert result["game_over"] is True

        # Recorder must be toggled on at start and off on exit — otherwise
        # the bridge would keep streaming after the run ended.
        modes = [c["recording_mode"] for c in env.recording_commands]
        assert modes == [True, False]

    def test_human_runner_respects_cancel_event(self, tmp_path):
        """A pre-set cancel_event must break out of the poll loop with
        RunCancelled, matching the AI runner's contract."""
        env = _FakeHumanEnv()
        agent = HumanAgent()
        rl = ReplayLogger(log_dir=str(tmp_path))
        ev = threading.Event()
        ev.set()

        # Initial drain still happens before cancel is checked.
        with patch("urllib.request.urlopen",
                   side_effect=[_make_events_response([])]):
            with pytest.raises(benchmark_runner.RunCancelled):
                benchmark_runner._run_episode_human(
                    env, agent, rl, max_steps=5,
                    cancel_event=ev, poll_interval=0.0,
                )

        # Recorder was turned on, then cleared in the finally block.
        modes = [c["recording_mode"] for c in env.recording_commands]
        assert modes == [True, False]
