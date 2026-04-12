"""Tests for YediEnv reward shaping.

Targets _compute_reward() directly so we don't need a live WebSocket bridge.
The unproductive-move penalty is enforced IN-GAME by the Unity bridge (mana
deduction); the Python env just reads the mana delta like it always did.
"""

from __future__ import annotations

import pytest

from yedi_benchmark.yedi_env import YediEnv


def _make_env():
    # __init__ creates a WebSocket object lazily, so we can build the env
    # without a live server as long as we don't call step()/reset().
    return YediEnv(server_url="ws://unused", max_steps=100)


def _state(mana=200, mana_max=200, game_over=False):
    return {
        "mana": mana,
        "mana_max": mana_max,
        "game_over": game_over,
        "slots": [],
    }


class TestBaseReward:
    def test_mana_delta_drives_reward(self):
        env = _make_env()
        env._prev_mana = 100
        env._prev_mana_max = 100
        # mana_max equals prev_mana_max so the new-max bonus branch doesn't fire
        env._state = _state(mana=150, mana_max=100)
        reward = env._compute_reward()
        # +50 mana -> +0.5
        assert reward == pytest.approx(0.5)

    def test_negative_delta(self):
        env = _make_env()
        env._prev_mana = 200
        env._prev_mana_max = 200
        env._state = _state(mana=180, mana_max=200)
        # delta = -0.2; mana_max (200) not > prev_mana_max (200), no bonus
        assert env._compute_reward() == pytest.approx(-0.2)

    def test_game_over_penalty_fires_on_mana_zero(self):
        env = _make_env()
        env._prev_mana = 5
        env._prev_mana_max = 5
        env._state = _state(mana=0, mana_max=5, game_over=True)
        # delta=-5 -> -0.05, plus -1.0 game over (mana actually bottomed out)
        assert env._compute_reward() == pytest.approx(-1.05)

    def test_game_over_penalty_skipped_on_timer_expiry(self):
        """Timer-based game_over should NOT trigger the -1.0 penalty, otherwise
        every run-to-completion episode eats a constant confound."""
        env = _make_env()
        env._prev_mana = 180
        env._prev_mana_max = 250
        # Timer expired with mana still positive
        env._state = _state(mana=175, mana_max=250, game_over=True)
        # delta=-5 -> -0.05, no game over penalty
        assert env._compute_reward() == pytest.approx(-0.05)

    def test_unproductive_move_penalty_flows_through_mana_delta(self):
        """The Unity bridge deducts 5 mana when an agent shuffles a card
        between build slots without merging. From the Python env's view,
        that's just a regular mana drop — no special handling needed, the
        reward-shaping term is the plain delta / 100."""
        env = _make_env()
        env._prev_mana = 200
        env._prev_mana_max = 200
        # 5 mana deducted in-game -> env sees mana=195
        env._state = _state(mana=195, mana_max=200)
        assert env._compute_reward() == pytest.approx(-0.05)
