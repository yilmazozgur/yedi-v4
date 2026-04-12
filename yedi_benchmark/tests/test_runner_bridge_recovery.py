"""Tests for the runner's per-episode bridge-failure recovery.

The motivating incident: an agent run died with ``bridge error for draw_card:
timeout`` after seven episodes. The whole run was marked FAILED, even though
17 episodes were never even attempted. This was the right behaviour for the
old code (a single bridge timeout was treated as fatal) but it meant a
backgrounded browser tab could nuke an entire benchmark.

What we now want:
  - Per-episode try/except for ``BridgeDisconnectedError``: log it, record
    it on the run record, recreate the env, and continue.
  - A consecutive-failure budget: if too many in a row hit the bridge, give
    up — the bridge is genuinely dead and there's no point burning more
    30s waits.
  - Run is marked COMPLETED if at least one episode succeeded; FAILED if
    every episode in the run hit the bridge.

These tests fake YediEnv so they don't require an actual browser bridge.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from yedi_benchmark import benchmark_runner
from yedi_benchmark.benchmark_runner import (
    MAX_CONSECUTIVE_BRIDGE_FAILURES,
    run_benchmark_with_registry,
)
from yedi_benchmark.registries import (
    AgentRegistry,
    PromptRegistry,
    RunRegistry,
    RunStatus,
)
from yedi_benchmark.yedi_env import BridgeDisconnectedError


# ──────────────────────────────────────────────────────────────────────────────
# Fake env that follows a scripted reset/step/close sequence
# ──────────────────────────────────────────────────────────────────────────────


class _ScriptedEnv:
    """Drop-in YediEnv replacement that follows a scripted failure plan.

    Pass a list of "OK" / "FAIL" / "FAIL_RESET" markers for episodes:
      - "OK"          -> reset+step succeed, episode terminates after one step
      - "FAIL"        -> reset succeeds, the first step raises BridgeDisconnectedError
      - "FAIL_RESET"  -> reset() itself raises BridgeDisconnectedError

    The class tracks instances per call so the test can assert that the
    runner recreated the env after a failure.
    """

    instances: list["_ScriptedEnv"] = []
    plan: list[str] = []
    _plan_idx = 0

    def __init__(self, server_url=None, game_config=None, max_steps=None):
        self.server_url = server_url
        self.game_config = game_config or {}
        self.max_steps = max_steps
        self.reset_calls = 0
        self.step_calls = 0
        self.closed = False
        _ScriptedEnv.instances.append(self)

    @classmethod
    def _next_marker(cls) -> str:
        marker = cls.plan[cls._plan_idx] if cls._plan_idx < len(cls.plan) else "OK"
        cls._plan_idx += 1
        return marker

    @classmethod
    def reset_plan(cls, plan):
        cls.plan = list(plan)
        cls._plan_idx = 0
        cls.instances = []

    def reset(self, seed=None, options=None):
        marker = self._next_marker()
        self._current_marker = marker
        if marker == "FAIL_RESET":
            raise BridgeDisconnectedError("reset bridge timeout")
        self.reset_calls += 1
        return self._obs(), self._info()

    def step(self, action):
        self.step_calls += 1
        if self._current_marker == "FAIL":
            raise BridgeDisconnectedError("step bridge timeout")
        # Episode terminates after a single step so the runner moves on.
        return self._obs(), 0.0, True, False, self._info()

    def close(self):
        self.closed = True

    @staticmethod
    def _obs():
        return {"action_mask": np.ones(37, dtype=np.int8)}

    @staticmethod
    def _info():
        return {"raw_state": {"mana": 100, "mana_max": 100}, "max_mana": 100}


# ──────────────────────────────────────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def setup(isolated_data_dir, isolated_runs_dir, monkeypatch):
    """Isolate registries + monkeypatch YediEnv with the scripted fake.

    Returns (run_registry,) — tests pull the agent_id off the seeded
    Random agent themselves.
    """
    monkeypatch.setattr(benchmark_runner, "YediEnv", _ScriptedEnv)
    monkeypatch.setattr(benchmark_runner, "YediVLMEnv", _ScriptedEnv)
    return RunRegistry()


def _random_agent_id() -> str:
    return AgentRegistry().get_by_name("Random").id


# ──────────────────────────────────────────────────────────────────────────────
# Per-episode failure recovery
# ──────────────────────────────────────────────────────────────────────────────


class TestPerEpisodeRecovery:
    def test_clean_run_records_no_errors(self, setup):
        """Sanity baseline: a run with zero bridge issues completes cleanly."""
        rr = setup
        _ScriptedEnv.reset_plan(["OK", "OK", "OK"])

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=3,
            max_steps=5,
        )

        assert result.status == RunStatus.COMPLETED
        assert result.episode_errors == []
        assert result.episodes_done() == 3
        assert len(result.results["easy_math_add"].episodes) == 3

    def test_one_episode_failure_does_not_kill_run(self, setup):
        """The whole point of this fix: a single bridge blip records an
        error, recreates the env, and the next episode runs normally."""
        rr = setup
        _ScriptedEnv.reset_plan(["OK", "FAIL", "OK"])

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=3,
            max_steps=5,
        )

        assert result.status == RunStatus.COMPLETED
        assert result.episodes_done() == 2  # one failed, two succeeded
        assert len(result.episode_errors) == 1
        assert result.episode_errors[0]["config"] == "easy_math_add"
        assert result.episode_errors[0]["episode_idx"] == 1
        assert "step bridge timeout" in result.episode_errors[0]["error"]
        # We created 1 initial env + 1 replacement after the failure = 2
        assert len(_ScriptedEnv.instances) >= 2
        assert _ScriptedEnv.instances[0].closed is True

    def test_failure_at_first_episode_recovers(self, setup):
        """Bridge failure on episode 0 must not stop later episodes."""
        rr = setup
        _ScriptedEnv.reset_plan(["FAIL", "OK", "OK"])

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=3,
            max_steps=5,
        )

        assert result.status == RunStatus.COMPLETED
        assert result.episodes_done() == 2
        assert len(result.episode_errors) == 1

    def test_bridge_failure_inside_reset_recorded(self, setup):
        """A reset()-time bridge failure (start_game timeout) must be
        caught and recovered from, just like a step()-time failure."""
        rr = setup
        _ScriptedEnv.reset_plan(["OK", "FAIL_RESET", "OK"])

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=3,
            max_steps=5,
        )

        assert result.status == RunStatus.COMPLETED
        assert result.episodes_done() == 2
        assert len(result.episode_errors) == 1
        assert "reset bridge timeout" in result.episode_errors[0]["error"]


# ──────────────────────────────────────────────────────────────────────────────
# Consecutive-failure budget
# ──────────────────────────────────────────────────────────────────────────────


class TestConsecutiveFailureBudget:
    def test_consecutive_failures_abort_run(self, setup):
        """N consecutive failures must trip the budget and mark the run
        FAILED so the suite doesn't burn the next 30s wait per episode."""
        rr = setup
        # MAX failures in a row -> abort
        _ScriptedEnv.reset_plan(["FAIL"] * MAX_CONSECUTIVE_BRIDGE_FAILURES)

        with pytest.raises(BridgeDisconnectedError, match="aborting"):
            run_benchmark_with_registry(
                agent_id=_random_agent_id(),
                mode="metadata-a",
                config_names=["easy_math_add"],
                episodes_per_config=MAX_CONSECUTIVE_BRIDGE_FAILURES,
                max_steps=5,
            )

        # The most recently created run should be FAILED with the budget
        # message in its error field.
        latest = rr.list()[0]
        assert latest.status == RunStatus.FAILED
        assert "aborting" in latest.error
        assert len(latest.episode_errors) == MAX_CONSECUTIVE_BRIDGE_FAILURES

    def test_one_success_resets_consecutive_counter(self, setup):
        """The counter must reset on every successful episode so a run
        with intermittent flakes doesn't trip the budget."""
        rr = setup
        # Pattern: FAIL, OK, FAIL, OK, FAIL — interleaved, no run of MAX
        _ScriptedEnv.reset_plan(["FAIL", "OK", "FAIL", "OK", "FAIL"])

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=5,
            max_steps=5,
        )

        # Run completes — never had MAX_CONSECUTIVE in a row
        assert result.status == RunStatus.COMPLETED
        assert result.episodes_done() == 2
        assert len(result.episode_errors) == 3

    def test_zero_successes_marks_failed_even_below_budget(self, setup):
        """If literally no episode succeeded but the consecutive budget
        wasn't tripped (e.g. only 2 episodes total), the run must still
        be FAILED — a run with zero data is not 'completed'."""
        rr = setup
        # Below the budget but still all-fail
        n = max(1, MAX_CONSECUTIVE_BRIDGE_FAILURES - 1)
        _ScriptedEnv.reset_plan(["FAIL"] * n)

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=n,
            max_steps=5,
        )

        assert result.status == RunStatus.FAILED
        assert "all" in result.error
        assert len(result.episode_errors) == n


# ──────────────────────────────────────────────────────────────────────────────
# Cancel still works alongside the new error recovery
# ──────────────────────────────────────────────────────────────────────────────


class TestCancelStillWorks:
    def test_cancel_set_before_run_marks_cancelled(self, setup):
        """A pre-set cancel_event must yield CANCELLED, even when the
        plan would otherwise route through the new bridge-recovery path."""
        rr = setup
        _ScriptedEnv.reset_plan(["OK", "FAIL", "OK", "OK", "OK"])

        ev = threading.Event()
        ev.set()

        result = run_benchmark_with_registry(
            agent_id=_random_agent_id(),
            mode="metadata-a",
            config_names=["easy_math_add"],
            episodes_per_config=5,
            max_steps=5,
            cancel_event=ev,
        )

        assert result.status == RunStatus.CANCELLED
