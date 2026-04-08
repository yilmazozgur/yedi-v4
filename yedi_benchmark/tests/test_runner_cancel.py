"""Tests for cooperative cancellation inside benchmark_runner.run_episode.

Background: clicking Cancel in the dashboard sets a threading.Event on the
RunExecutor. Before this fix, that flag was only checked between configs and
between episodes — never inside a single episode. A long episode (100 steps,
each step potentially a 30s LLM call plus 30-120s rate-limit retry) could
ignore the cancel for many minutes.

These tests pin the new contract: ``run_episode`` checks ``cancel_event`` at
the top of every step iteration and raises ``RunCancelled`` so the worker
exits at the next step boundary.
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from yedi_benchmark.benchmark_runner import RunCancelled, run_episode


class _FakeEnv:
    """Minimal env stub: always returns the same obs/info, never terminates."""

    def __init__(self):
        self.game_config = {"modes": {}}
        self.reset_calls = 0
        self.step_calls = 0

    def reset(self):
        self.reset_calls += 1
        return self._obs(), self._info()

    def step(self, action):
        self.step_calls += 1
        return self._obs(), 0.0, False, False, self._info()

    def close(self):
        pass

    @staticmethod
    def _obs():
        return {"action_mask": np.ones(38, dtype=np.int8)}

    @staticmethod
    def _info():
        return {"raw_state": {"mana": 200, "mana_max": 200}, "max_mana": 200}


class _FakeAgent:
    """Records every act() call. Optionally sets a cancel_event partway."""

    def __init__(self, name: str = "fake", trip_event_at: int = -1, event=None):
        self.name = name
        self.acts = 0
        self.reset_calls = 0
        self.results = []
        self._trip_at = trip_event_at
        self._event = event

    def reset(self):
        self.reset_calls += 1

    def act(self, obs, info):
        self.acts += 1
        # Simulate the user clicking Cancel mid-episode by tripping the event
        # from inside an act() call. The next iteration of run_episode's loop
        # should see the flag and bail out.
        if self._event is not None and self.acts == self._trip_at:
            self._event.set()
        return 0  # always action 0

    def on_step_result(self, action, reward, terminated, info):
        self.results.append((action, reward, terminated))


class TestRunEpisodeCancel:
    def test_no_event_runs_to_completion(self):
        """Sanity: with no cancel_event, run_episode is unchanged."""
        env = _FakeEnv()
        agent = _FakeAgent()
        result = run_episode(env, agent, replay_logger=None, max_steps=5)
        assert result["steps"] == 5
        assert agent.acts == 5
        assert env.step_calls == 5

    def test_unset_event_runs_to_completion(self):
        """An event that's never set must not affect the run."""
        env = _FakeEnv()
        ev = threading.Event()
        agent = _FakeAgent(event=ev, trip_event_at=-1)
        result = run_episode(
            env, agent, replay_logger=None, max_steps=5, cancel_event=ev,
        )
        assert result["steps"] == 5
        assert agent.acts == 5

    def test_event_set_before_first_step_aborts_immediately(self):
        """An event already set when run_episode starts must short-circuit
        before any step runs."""
        env = _FakeEnv()
        ev = threading.Event()
        ev.set()
        agent = _FakeAgent(event=None)

        with pytest.raises(RunCancelled, match="cancelled"):
            run_episode(
                env, agent, replay_logger=None, max_steps=5, cancel_event=ev,
            )
        assert agent.acts == 0
        assert env.step_calls == 0

    def test_event_set_mid_episode_aborts_at_next_step(self):
        """The whole point of this fix: an event set during step N must be
        observed at the top of step N+1's loop iteration, before another
        agent.act() call burns time."""
        env = _FakeEnv()
        ev = threading.Event()
        # Trip the event from inside the 3rd act() call. The 4th iteration's
        # cancel check fires before agent.act() is called again.
        agent = _FakeAgent(event=ev, trip_event_at=3)

        with pytest.raises(RunCancelled, match="cancelled"):
            run_episode(
                env, agent, replay_logger=None, max_steps=10, cancel_event=ev,
            )
        # Three full steps ran, the 4th was aborted before act()
        assert agent.acts == 3
        assert env.step_calls == 3
