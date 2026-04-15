"""Tests for the WebSocket bridge failure paths.

These tests cover the cascade we saw in production: a Claude run died with
``RuntimeError: Unexpected ASGI message 'websocket.send'`` from inside
``GameConnection.send`` when the user closed the browser tab mid-run, and
``yedi_env._send_command`` then surfaced ``no close frame received or sent``
to the runner — which marked the run FAILED with a cryptic message.

What we want to assert here:

1. ``GameConnection.send`` catches transport errors, marks the bridge dead,
   and converts them to ``BridgeError``.
2. ``GameConnection.mark_dead`` is idempotent and fails any in-flight pending
   futures so the agent loop doesn't sit on a 30s timeout.
3. ``YediEnv._send_command`` catches ``ConnectionClosed`` and turns it into
   ``BridgeDisconnectedError``.
4. ``YediEnv._send_command`` parses ``{"error": ..., "seq": ...}`` payloads
   from the server and raises ``BridgeDisconnectedError`` instead of returning
   them as if they were valid state.
5. The ``"ok"`` path is unchanged: a regular state response still passes
   through ``_send_command`` cleanly.

We use plain ``asyncio.run`` for the async cases so the suite stays runnable
without pytest-asyncio (which isn't a project dependency).
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from yedi_benchmark import gym_server
from yedi_benchmark.gym_server import (
    HEARTBEAT_SEQ,
    AgentConnection,
    BridgeError,
    GameConnection,
)
from yedi_benchmark.yedi_env import BridgeDisconnectedError, YediEnv


def _run(coro):
    """Run an awaitable to completion on a fresh event loop.

    We can't use ``asyncio.run`` because we sometimes create futures bound to a
    specific loop in fixtures; this helper makes the loop explicit.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ──────────────────────────────────────────────────────────────────────────────
# Server-side: GameConnection.send & mark_dead
# ──────────────────────────────────────────────────────────────────────────────


class TestGameConnectionSend:
    @pytest.fixture(autouse=True)
    def _isolate_globals(self, monkeypatch):
        """Reset gym_server module globals so tests don't bleed into each other."""
        monkeypatch.setattr(gym_server, "game_connection", None)
        monkeypatch.setattr(gym_server, "agent_connection", None)
        yield

    def test_send_succeeds_on_healthy_socket(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()
        conn = GameConnection(ws)

        _run(conn.send({"type": "draw_card"}))

        ws.send_json.assert_awaited_once_with({"type": "draw_card"})
        assert conn.connected is True

    def test_send_on_disconnected_raises_bridge_error(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()
        conn = GameConnection(ws)
        conn.connected = False

        with pytest.raises(BridgeError, match="closed"):
            _run(conn.send({"type": "draw_card"}))
        ws.send_json.assert_not_awaited()

    def test_send_wraps_runtime_error_as_bridge_error(self):
        """The exact failure mode we hit: starlette's
        'Unexpected ASGI message websocket.send' RuntimeError."""
        ws = MagicMock()
        ws.send_json = AsyncMock(
            side_effect=RuntimeError(
                "Unexpected ASGI message 'websocket.send', after sending 'websocket.close'"
            )
        )
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        with pytest.raises(BridgeError, match="game send failed"):
            _run(conn.send({"type": "draw_card"}))

        # Bridge marked itself dead and cleared the global pointer
        assert conn.connected is False
        assert gym_server.game_connection is None

    def test_send_failure_fails_pending_agent_futures(self):
        """When the game ws dies mid-flight, in-flight pending requests on the
        agent connection must be settled with BridgeError so the agent loop
        does not block on the 30s timeout."""
        ws = MagicMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("transport closed"))
        game = GameConnection(ws)
        gym_server.game_connection = game

        agent_ws = MagicMock()
        agent = AgentConnection(agent_ws)
        gym_server.agent_connection = agent

        loop = asyncio.new_event_loop()
        try:
            future_a = loop.create_future()
            future_b = loop.create_future()
            agent.pending_responses[1] = future_a
            agent.pending_responses[2] = future_b

            with pytest.raises(BridgeError):
                loop.run_until_complete(game.send({"type": "draw_card", "seq": 99}))

            assert future_a.done()
            assert future_b.done()
            with pytest.raises(BridgeError, match="lost"):
                future_a.result()
            with pytest.raises(BridgeError, match="lost"):
                future_b.result()
            assert agent.pending_responses == {}
        finally:
            loop.close()

    def test_mark_dead_is_idempotent(self):
        ws = MagicMock()
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        conn.mark_dead()
        # Second call must not throw or re-clear globals already cleared.
        conn.mark_dead()
        assert conn.connected is False


# ──────────────────────────────────────────────────────────────────────────────
# Server-side: AgentConnection.send_command surfaces BridgeError
# ──────────────────────────────────────────────────────────────────────────────


class TestAgentConnectionSendCommand:
    @pytest.fixture(autouse=True)
    def _isolate_globals(self, monkeypatch):
        monkeypatch.setattr(gym_server, "game_connection", None)
        monkeypatch.setattr(gym_server, "agent_connection", None)
        yield

    def test_send_command_no_game_raises_bridge_error(self):
        agent = AgentConnection(MagicMock())
        gym_server.agent_connection = agent

        with pytest.raises(BridgeError, match="no game connected"):
            _run(agent.send_command({"type": "draw_card"}))
        # Pending dict must be empty so we don't leak futures
        assert agent.pending_responses == {}

    def test_send_command_propagates_send_failure(self):
        ws = MagicMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("dead transport"))
        game = GameConnection(ws)
        gym_server.game_connection = game

        agent = AgentConnection(MagicMock())
        gym_server.agent_connection = agent

        with pytest.raises(BridgeError):
            _run(agent.send_command({"type": "draw_card"}))
        # The pending entry for this seq was cleaned up
        assert agent.pending_responses == {}


# ──────────────────────────────────────────────────────────────────────────────
# Env-side: YediEnv._send_command failure detection
# ──────────────────────────────────────────────────────────────────────────────


def _make_env(send_response):
    """Build a YediEnv instance with a fake ws/loop wired in.

    ``send_response`` is the value the fake ``recv()`` will return (or an
    Exception subclass to raise instead).
    """
    env = YediEnv.__new__(YediEnv)  # bypass __init__ — no real ws needed
    env._loop = asyncio.new_event_loop()

    fake_ws = MagicMock()
    fake_ws.send = AsyncMock()

    if isinstance(send_response, BaseException) or (
        isinstance(send_response, type) and issubclass(send_response, BaseException)
    ):
        fake_ws.recv = AsyncMock(side_effect=send_response)
    else:
        fake_ws.recv = AsyncMock(return_value=send_response)

    env._ws = fake_ws
    return env


class TestYediEnvSendCommand:
    def test_returns_state_on_ok_response(self):
        env = _make_env(json.dumps({"mana": 250, "type": "state", "seq": 1}))
        try:
            result = env._send_command({"type": "get_state"})
            assert result["mana"] == 250
        finally:
            env._loop.close()

    def test_raises_on_error_payload(self):
        env = _make_env(json.dumps({"error": "no game connected", "seq": 1}))
        try:
            with pytest.raises(BridgeDisconnectedError, match="no game connected"):
                env._send_command({"type": "draw_card"})
        finally:
            env._loop.close()

    def test_raises_on_connection_closed(self):
        from websockets.exceptions import ConnectionClosedError

        # ConnectionClosedError signature varies across websockets versions.
        try:
            err = ConnectionClosedError(None, None)
        except TypeError:
            err = ConnectionClosedError(1006, "abnormal closure")  # type: ignore[call-arg]

        env = _make_env(err)
        try:
            with pytest.raises(BridgeDisconnectedError, match="closed"):
                env._send_command({"type": "draw_card"})
            # Dead socket should have been dropped
            assert env._ws is None
        finally:
            env._loop.close()

    def test_raises_on_recv_timeout(self):
        # Wait_for raises TimeoutError when the inner future never completes;
        # use a never-resolving recv to force that path.
        async def never(*_args, **_kwargs):
            await asyncio.sleep(10)

        env = YediEnv.__new__(YediEnv)
        env._loop = asyncio.new_event_loop()
        fake_ws = MagicMock()
        fake_ws.send = AsyncMock()
        fake_ws.recv = never
        env._ws = fake_ws

        try:
            with pytest.raises(BridgeDisconnectedError, match="timed out"):
                env._send_command({"type": "draw_card"}, timeout=0.05)
        finally:
            env._loop.close()

    def test_error_response_with_state_passthrough(self):
        """An ``{"error": ...}`` payload that ALSO carries state (e.g. recoverable
        invalid action ack) should pass through, not raise. The bridge-failure
        sentinel is specifically the bare ``{"error": ..., "seq": ...}`` form
        the server sends when the game is dead."""
        env = _make_env(json.dumps({"error": "invalid move", "mana": 200, "seq": 1}))
        try:
            result = env._send_command({"type": "move_card"})
            assert result["error"] == "invalid move"
            assert result["mana"] == 200
        finally:
            env._loop.close()


# ──────────────────────────────────────────────────────────────────────────────
# _wait_for_fresh_state — readiness probe that replaced the old time.sleep(3.0)
# scene-load race in YediEnv.reset(). The race silently lost ~50% of EASY-tier
# Qwen3-VL episodes because the env would build its first observation off a
# stale post-game-over state (mana=0, no valid actions, no slots). The probe
# retries get_state until the response actually looks like a fresh game.
# ──────────────────────────────────────────────────────────────────────────────


def _fresh_state(**overrides):
    """Minimal state dict that satisfies _is_fresh_state."""
    base = {
        "type": "state", "mana": 200, "mana_max": 200,
        "action_count": 0, "max_steps": 100,
        "slots": [{"occupied": False} for _ in range(7)],
        "valid_actions": [0], "seq": 1,
    }
    base.update(overrides)
    return base


def _stale_state(**overrides):
    """A state matching the post-game-over leak that triggered the bug:
    mana=0, no valid actions, lingering action_count from the prior run."""
    base = {
        "type": "state", "mana": 0, "mana_max": 0,
        "action_count": 199, "max_steps": 200,
        "slots": [],
        "valid_actions": [], "seq": 1,
    }
    base.update(overrides)
    return base


class TestIsFreshState:
    """Boundary checks for _is_fresh_state — the predicate the polling loop
    uses to decide whether the bridge has finished loading the new scene."""

    def test_fresh_state_passes(self):
        assert YediEnv._is_fresh_state(_fresh_state()) is True

    def test_stale_state_rejected(self):
        assert YediEnv._is_fresh_state(_stale_state()) is False

    def test_zero_mana_rejected(self):
        assert YediEnv._is_fresh_state(_fresh_state(mana=0)) is False

    def test_empty_valid_actions_rejected(self):
        assert YediEnv._is_fresh_state(_fresh_state(valid_actions=[])) is False

    def test_nonzero_action_count_rejected(self):
        # Stale frame: bridge still reporting the previous episode's last step.
        assert YediEnv._is_fresh_state(_fresh_state(action_count=42)) is False

    def test_missing_action_count_rejected(self):
        # Defensive: pre-fix bridge omitted the field entirely. We'd rather
        # poll again than trust an under-populated frame.
        s = _fresh_state()
        del s["action_count"]
        assert YediEnv._is_fresh_state(s) is False

    def test_non_dict_rejected(self):
        assert YediEnv._is_fresh_state(None) is False
        assert YediEnv._is_fresh_state("oops") is False

    # ── Strict-freshness checks: the additions that catch the TOC/TOU
    # ── mash-up frame observed in run_1ffefc335187. Each test below
    # ── corresponds to one symptom of that bug.

    def test_occupied_slot_rejected_even_if_action_count_zero(self):
        """The exact bug case: HeptagonController scene reset its
        counter to 0, but the prior episode's slot game objects are
        still alive. Old check passed; new check must reject."""
        s = _fresh_state(mana=81, mana_max=193)
        # Match the observed mash-up: slot 1 has Num=2, slot 3 has 1 merge
        s["slots"] = [
            {"occupied": False},
            {"occupied": True, "card_mana": 9, "merges_done": 0,
             "number_value": 2.0},
            {"occupied": False},
            {"occupied": True, "card_mana": 9, "merges_done": 1,
             "number_value": 0.0},
            {"occupied": False},
            {"occupied": False},
            {"occupied": False},
        ]
        assert YediEnv._is_fresh_state(s) is False

    def test_any_occupied_slot_rejected(self):
        """Even one occupied slot is enough to disqualify a fresh state."""
        for occ_idx in range(7):
            s = _fresh_state()
            s["slots"][occ_idx] = {"occupied": True, "card_mana": 5, "merges_done": 0}
            assert YediEnv._is_fresh_state(s) is False, f"slot {occ_idx} occupied should reject"

    def test_missing_slots_rejected(self):
        """A truly fresh game always serializes the 7-slot array.
        A missing list is the bridge being mid-load."""
        s = _fresh_state()
        del s["slots"]
        assert YediEnv._is_fresh_state(s) is False

    def test_empty_slots_list_rejected(self):
        """Slots present but empty list — also a not-yet-spawned signal."""
        s = _fresh_state(slots=[])
        assert YediEnv._is_fresh_state(s) is False

    def test_stale_mana_max_rejected(self):
        """Mana_max from prior episode bleeding through. The mash-up frame
        had mana=81 / mana_max=193 — clearly inconsistent."""
        s = _fresh_state(mana=81, mana_max=193)
        # Make the slots empty so the only failing condition is mana_max.
        assert YediEnv._is_fresh_state(s) is False

    def test_mana_max_zero_accepted(self):
        """Pre-init mana_max==0 is fine — many fresh frames look like this."""
        s = _fresh_state(mana=200, mana_max=0)
        assert YediEnv._is_fresh_state(s) is True

    def test_mana_max_equal_to_mana_accepted(self):
        """The bridge initializes mana_max to the starting mana once the
        game is actually running. mana_max == mana on a fresh frame is
        the steady state."""
        s = _fresh_state(mana=200, mana_max=200)
        assert YediEnv._is_fresh_state(s) is True

    def test_mana_max_close_to_mana_accepted(self):
        """Tolerate sub-half-mana float jitter (e.g. 200.0 vs 200.0000061)."""
        s = _fresh_state(mana=200.0, mana_max=200.0000061)
        assert YediEnv._is_fresh_state(s) is True


class TestIsBrokenLoadingState:
    """The 'scene loading' sentinel that step() uses to bail out of a
    ghost episode. The signature came from the run_1ffefc335187 trace
    inspection: post-step-0 frames where the bridge handed back
    Mana=0 / Best=0 / Step=?/? for the entire remaining 199 steps."""

    def _blank(self, **overrides):
        s = {
            "type": "state", "mana": 0, "mana_max": 0,
            "action_count": None,  # the literal None — the sentinel
            "max_steps": None,
            "slots": [],
            "valid_actions": [],
        }
        s.update(overrides)
        return s

    def test_blank_sentinel_detected(self):
        assert YediEnv._is_broken_loading_state(self._blank()) is True

    def test_non_dict_treated_as_broken(self):
        assert YediEnv._is_broken_loading_state(None) is True
        assert YediEnv._is_broken_loading_state("oops") is True

    def test_real_state_not_broken(self):
        # Normal mid-episode frame with low mana but real data
        s = _fresh_state(mana=50, mana_max=200, action_count=42)
        s["slots"][1] = {"occupied": True, "card_mana": 9, "merges_done": 0}
        assert YediEnv._is_broken_loading_state(s) is False

    def test_mana_zero_alone_is_not_broken(self):
        """Mana legitimately can hit 0 mid-game; that ALONE must not
        trigger the bail-out. Only the full sentinel (no slots, no
        valid_actions, action_count=None) qualifies."""
        s = self._blank(action_count=80, valid_actions=[0])
        assert YediEnv._is_broken_loading_state(s) is False

    def test_action_count_zero_int_is_not_broken(self):
        """action_count=0 (the int) must NOT match — only None does.
        Otherwise we'd misfire on the very first step of every game."""
        s = self._blank(action_count=0)
        assert YediEnv._is_broken_loading_state(s) is False

    def test_occupied_slot_disqualifies_sentinel(self):
        """If any slot is occupied, the bridge clearly has real game
        state — not a blank loading frame."""
        s = self._blank()
        s["slots"] = [{"occupied": True, "card_mana": 9, "merges_done": 0}]
        assert YediEnv._is_broken_loading_state(s) is False

    def test_valid_actions_present_disqualifies_sentinel(self):
        s = self._blank(valid_actions=[0])
        assert YediEnv._is_broken_loading_state(s) is False


class TestStepRaisesOnBrokenState:
    """Integration check: when the bridge starts returning the loading
    sentinel mid-episode, step() must raise BridgeDisconnectedError so
    the runner's recovery path kicks in instead of grinding through 200
    wasted LLM calls."""

    def _make_env(self, response, monkeypatch):
        env = YediEnv.__new__(YediEnv)
        env._ws = MagicMock()
        env._loop = None
        env._state = _fresh_state(mana=200, mana_max=200)
        env._prev_mana = 200.0
        env._prev_mana_max = 200.0
        env._step_count = 0
        env.max_steps = 100

        def fake_send(command, timeout=30.0):
            return response
        monkeypatch.setattr(env, "_send_command", fake_send)
        return env

    def test_step_raises_on_blank_sentinel(self, monkeypatch):
        blank = {
            "type": "state", "mana": 0, "mana_max": 0,
            "action_count": None, "slots": [], "valid_actions": [],
        }
        env = self._make_env(blank, monkeypatch)
        with pytest.raises(BridgeDisconnectedError, match="scene loading"):
            env.step(0)

    def test_step_does_not_raise_on_normal_state(self, monkeypatch):
        # Normal post-action state with real fields — must NOT raise.
        normal = {
            "type": "state", "mana": 190, "mana_max": 200,
            "action_count": 1, "max_steps": 100,
            "slots": [{"occupied": False} for _ in range(7)],
            "valid_actions": [0], "game_over": False,
            "timer_remaining": 10.0, "beat_phase": 0.0,
        }
        env = self._make_env(normal, monkeypatch)
        obs, reward, term, trunc, info = env.step(0)
        assert term is False
        assert env._step_count == 1

    def test_step_does_not_raise_on_low_mana_real_frame(self, monkeypatch):
        """Defensive: a legitimate near-game-over frame (mana=0 but
        action_count and slots intact) must NOT trigger the sentinel."""
        near_loss = {
            "type": "state", "mana": 0, "mana_max": 200,
            "action_count": 99, "max_steps": 100,
            "slots": [{"occupied": False} for _ in range(7)],
            "valid_actions": [], "game_over": True,
            "timer_remaining": 0.0, "beat_phase": 0.0,
        }
        env = self._make_env(near_loss, monkeypatch)
        obs, reward, term, trunc, info = env.step(0)
        assert term is True


class TestWaitForFreshState:
    """The polling loop itself: returns on first fresh frame, retries past
    stale frames, raises on timeout."""

    def _make_env_with_responses(self, responses, monkeypatch):
        """Build a bare YediEnv whose _send_command returns successive items
        from `responses` (last item repeats forever)."""
        env = YediEnv.__new__(YediEnv)
        env._ws = MagicMock()  # _ensure_connected() no-op

        idx = {"i": 0}
        def fake_send(command, timeout=30.0):
            i = min(idx["i"], len(responses) - 1)
            idx["i"] += 1
            return responses[i]

        monkeypatch.setattr(env, "_send_command", fake_send)
        # Polling sleeps 200ms between attempts; patch it out so the
        # test runs in microseconds rather than real time.
        import yedi_benchmark.yedi_env as yedi_env_mod
        monkeypatch.setattr(yedi_env_mod.time, "sleep", lambda *_a, **_k: None)
        return env

    def test_returns_immediately_on_fresh_first_response(self, monkeypatch):
        env = self._make_env_with_responses([_fresh_state()], monkeypatch)
        result = env._wait_for_fresh_state(timeout=1.0)
        assert result["mana"] == 200
        assert result["action_count"] == 0

    def test_polls_past_stale_frames(self, monkeypatch):
        # Three stale frames (post-game-over leak) followed by a fresh one.
        # The probe must keep polling instead of accepting the first frame.
        # Note: mana_max must equal mana on the fresh frame — the strict
        # freshness check rejects inconsistent (mana, mana_max) pairs.
        responses = [
            _stale_state(),
            _stale_state(),
            _stale_state(),
            _fresh_state(mana=180, mana_max=180),
        ]
        env = self._make_env_with_responses(responses, monkeypatch)
        result = env._wait_for_fresh_state(timeout=5.0)
        assert result["mana"] == 180

    def test_raises_on_timeout_with_diagnostic(self, monkeypatch):
        # Stuck stale forever — the probe must give up loudly rather than
        # silently returning a corrupt frame.
        env = self._make_env_with_responses(
            [_stale_state(action_count=99, valid_actions=[])], monkeypatch
        )
        with pytest.raises(BridgeDisconnectedError, match="never produced a fresh state"):
            env._wait_for_fresh_state(timeout=0.05)

    def test_timeout_diagnostic_includes_last_seen_state(self, monkeypatch):
        # The error message should surface why we gave up — without this
        # diagnostic, the runner log just says "timeout" and the operator
        # has to dig through trace files to figure out what was happening.
        env = self._make_env_with_responses(
            [_stale_state(mana=0, action_count=199, valid_actions=[])],
            monkeypatch,
        )
        try:
            env._wait_for_fresh_state(timeout=0.05)
        except BridgeDisconnectedError as e:
            msg = str(e)
            assert "mana" in msg
            assert "action_count" in msg
            assert "199" in msg
            assert "valid_actions_count" in msg
        else:
            pytest.fail("expected BridgeDisconnectedError")

    def test_polls_past_unity_error_responses(self, monkeypatch):
        """Unity's AgentBridge sends {"type": "error", "message": "Game not
        ready"} while CacheReferencesDelayed hasn't finished. These lack a
        top-level "error" key so _send_command lets them through. The polling
        loop must recognise them and keep trying — not treat them as stale
        state (which left last_state = {} and produced the misleading
        {mana: None, action_count: None} diagnostic in run_fe6129041779)."""
        unity_error = {"type": "error", "message": "Game not ready", "seq": 1}
        responses = [
            unity_error,
            unity_error,
            unity_error,
            _fresh_state(),
        ]
        env = self._make_env_with_responses(responses, monkeypatch)
        result = env._wait_for_fresh_state(timeout=5.0)
        assert result["mana"] == 200
        assert result["action_count"] == 0

    def test_unity_error_timeout_shows_error_count(self, monkeypatch):
        """If we only ever get Unity error responses, the diagnostic should
        include the error count so the operator knows it's a scene-load
        problem, not a stale-state problem."""
        unity_error = {"type": "error", "message": "Game not ready", "seq": 1}
        env = self._make_env_with_responses([unity_error], monkeypatch)
        with pytest.raises(BridgeDisconnectedError, match="error_responses"):
            env._wait_for_fresh_state(timeout=0.05)

    def test_does_not_call_send_command_after_success(self, monkeypatch):
        """Once we've seen a fresh frame we must stop polling — extra
        get_state calls waste a roundtrip and could race the very command
        the caller is about to issue next."""
        call_count = {"n": 0}
        def fake_send(command, timeout=30.0):
            call_count["n"] += 1
            return _fresh_state()
        env = YediEnv.__new__(YediEnv)
        env._ws = MagicMock()
        monkeypatch.setattr(env, "_send_command", fake_send)
        import yedi_benchmark.yedi_env as yedi_env_mod
        monkeypatch.setattr(yedi_env_mod.time, "sleep", lambda *_a, **_k: None)

        env._wait_for_fresh_state(timeout=1.0)
        assert call_count["n"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# YediEnv.reset() — start_game command shape, including the perfect_memory
# ablation flag. We don't need a real bridge: monkey-patch _send_command to
# capture the outgoing command and return a stub state.
# ──────────────────────────────────────────────────────────────────────────────


def _make_reset_env(game_config: dict) -> YediEnv:
    env = YediEnv.__new__(YediEnv)
    env.game_config = game_config
    env._seed = None
    env.max_steps = 0
    env._state = None
    env._prev_mana = 0
    env._step_count = 0
    env._ws = MagicMock()  # presence makes _ensure_connected() a no-op
    env._loop = None
    return env


# ──────────────────────────────────────────────────────────────────────────────
# Heartbeat: GameConnection pings the game and marks dead on silence
# ──────────────────────────────────────────────────────────────────────────────


class TestGameConnectionHeartbeat:
    """The heartbeat task pings the game every HEARTBEAT_INTERVAL seconds
    and marks the bridge dead if it stays silent past HEARTBEAT_DEAD_AFTER.
    Without this, an agent on a 30s wait_for could sit on a hung
    backgrounded browser tab for the entire timeout. With it, the bridge
    fails fast and the runner's per-episode catch can recover within ~12s.
    """

    @pytest.fixture(autouse=True)
    def _isolate_globals(self, monkeypatch):
        monkeypatch.setattr(gym_server, "game_connection", None)
        monkeypatch.setattr(gym_server, "agent_connection", None)
        # Speed the heartbeat way up so tests don't take real seconds.
        monkeypatch.setattr(gym_server, "HEARTBEAT_INTERVAL_S", 0.01)
        monkeypatch.setattr(gym_server, "HEARTBEAT_DEAD_AFTER_S", 0.03)
        yield

    def test_heartbeat_pings_alive_connection(self):
        """A game that keeps touching the bridge stays alive."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        async def run():
            conn.start_heartbeat()
            # Touch every iteration so the heartbeat never gives up.
            for _ in range(5):
                await asyncio.sleep(0.005)
                conn.touch()
            assert conn.connected is True
            # At least one ping was sent
            assert ws.send_json.await_count >= 1
            sent = ws.send_json.call_args[0][0]
            assert sent["type"] == "ping"
            assert sent["seq"] == HEARTBEAT_SEQ
            conn.mark_dead()  # cancels the task

        _run(run())

    def test_heartbeat_marks_dead_on_silence(self):
        """If nothing touches the bridge past HEARTBEAT_DEAD_AFTER, the
        heartbeat task calls mark_dead and the bridge goes offline."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        async def run():
            conn.start_heartbeat()
            # Wait long enough for the dead-after window to elapse without
            # ever calling touch().
            for _ in range(20):
                if not conn.connected:
                    break
                await asyncio.sleep(0.01)
            assert conn.connected is False
            assert gym_server.game_connection is None

        _run(run())

    def test_heartbeat_marks_dead_on_send_failure(self):
        """A ping that fails to send (e.g. ASGI transport closed) must
        mark the bridge dead via the same path as a real send failure."""
        ws = MagicMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("transport gone"))
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        async def run():
            conn.start_heartbeat()
            for _ in range(20):
                if not conn.connected:
                    break
                # Touch to keep the dead-after timer fresh — we want the
                # mark_dead to come from the send failure, not from silence.
                conn.touch()
                await asyncio.sleep(0.01)
            assert conn.connected is False
            assert gym_server.game_connection is None

        _run(run())

    def test_mark_dead_cancels_heartbeat(self):
        """Calling mark_dead while the heartbeat is running must cancel
        the task so it doesn't keep firing on a dead connection."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        conn = GameConnection(ws)
        gym_server.game_connection = conn

        async def run():
            conn.start_heartbeat()
            await asyncio.sleep(0.005)  # let it spin up
            conn.mark_dead()
            # Give the cancelled task a beat to actually exit
            await asyncio.sleep(0.02)
            assert conn._heartbeat_task.done()

        _run(run())


class TestGameWebSocketVisibilityRoute:
    """The /ws/game route routes Page Visibility reports from the browser
    to BridgeStatus.set_tab_hidden(). The dashboard polls bridge status
    and shows a warning pill so the user knows a hidden tab is the cause
    when bridge timeouts start blowing up runs.

    These tests use FastAPI's TestClient to drive a real WebSocket round
    trip through the route handler — the routing logic is small but the
    consequence (warning pill in the dashboard) is the whole reason this
    pipeline exists, so an end-to-end check is worth it.

    Subtlety: ``mark_game_disconnected`` clears ``tab_hidden`` (so a stale
    "hidden" doesn't survive a tab close). That means we must observe the
    flag *while the WebSocket is still open*, not after the context exits.
    """

    @pytest.fixture(autouse=True)
    def _isolate_globals(self, monkeypatch):
        from yedi_benchmark import bridge_status as bs
        monkeypatch.setattr(gym_server, "game_connection", None)
        monkeypatch.setattr(gym_server, "agent_connection", None)
        bs.reset_bridge_status()
        yield
        bs.reset_bridge_status()

    @staticmethod
    def _wait_for(predicate, timeout: float = 2.0):
        """Spin until ``predicate()`` returns truthy, or raise after timeout.

        TestClient runs the FastAPI app on a background thread; the test
        thread can't directly observe when the server has finished
        processing a sent WebSocket message. We poll the side effect.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        raise AssertionError(f"predicate never became true within {timeout}s")

    def test_visibility_hidden_message_sets_flag(self):
        from fastapi.testclient import TestClient
        from yedi_benchmark.bridge_status import get_bridge_status

        with TestClient(gym_server.app) as client:
            with client.websocket_connect("/ws/game") as ws:
                ws.send_json({"type": "visibility", "hidden": True})
                # Observe the side effect *before* closing the ws — the
                # disconnect path clears the flag, which is correct
                # production behaviour but would mask the assertion.
                self._wait_for(lambda: get_bridge_status().is_tab_hidden() is True)

    def test_visibility_visible_message_clears_flag(self):
        from fastapi.testclient import TestClient
        from yedi_benchmark.bridge_status import get_bridge_status

        with TestClient(gym_server.app) as client:
            with client.websocket_connect("/ws/game") as ws:
                ws.send_json({"type": "visibility", "hidden": True})
                self._wait_for(lambda: get_bridge_status().is_tab_hidden() is True)
                ws.send_json({"type": "visibility", "hidden": False})
                self._wait_for(lambda: get_bridge_status().is_tab_hidden() is False)

    def test_visibility_message_not_forwarded_to_agent(self):
        """A visibility report is a server-side concern only — the gym
        env on the agent side should never see it. Otherwise it would
        show up as a phantom 'unrouted message' warning."""
        from fastapi.testclient import TestClient
        from yedi_benchmark.bridge_status import get_bridge_status

        # Wire up an agent connection that records any forwarded messages.
        forwarded: list[dict] = []

        class _RecordingAgent:
            connected = True
            pending_responses: dict = {}
            recording_mode = False

            def on_game_message(self, msg):
                forwarded.append(msg)

        gym_server.agent_connection = _RecordingAgent()

        with TestClient(gym_server.app) as client:
            with client.websocket_connect("/ws/game") as ws:
                ws.send_json({"type": "visibility", "hidden": True})
                # Wait for the side effect to land before closing — at
                # which point we know the server's receive loop has
                # processed the message and either forwarded or skipped.
                self._wait_for(lambda: get_bridge_status().is_tab_hidden() is True)

        assert forwarded == [], (
            f"visibility messages must not be forwarded to the agent route, "
            f"but got: {forwarded}"
        )

    def test_disconnect_clears_tab_hidden(self):
        """The disconnect path clears tab_hidden so a stale 'hidden' from
        a previous tab doesn't survive into the next connection."""
        from fastapi.testclient import TestClient
        from yedi_benchmark.bridge_status import get_bridge_status

        with TestClient(gym_server.app) as client:
            with client.websocket_connect("/ws/game") as ws:
                ws.send_json({"type": "visibility", "hidden": True})
                self._wait_for(lambda: get_bridge_status().is_tab_hidden() is True)
            # WebSocket closed → mark_dead → mark_game_disconnected →
            # tab_hidden cleared.
            self._wait_for(lambda: get_bridge_status().is_tab_hidden() is False)


class TestYediEnvResetCommand:
    def _patch_reset(self, env, monkeypatch):
        """Capture every _send_command call into a list and return canned state."""
        sent: list[dict] = []

        def fake_send(command, timeout=30.0):
            sent.append(command)
            # Reset() polls get_state until the response satisfies
            # _is_fresh_state — that requires mana > 0, non-empty
            # valid_actions, and action_count == 0. The canned dict
            # below meets all three so the polling loop returns on the
            # first pass instead of timing out.
            return {
                "type": "state", "mana": 200, "mana_max": 200,
                "action_count": 0, "max_steps": 100,
                "timer_remaining": 0.0, "beat_phase": 0.0,
                "slots": [{"occupied": False} for _ in range(7)],
                "valid_actions": [0], "seq": 1,
            }

        monkeypatch.setattr(env, "_send_command", fake_send)
        # _wait_for_fresh_state would otherwise burn real wall-clock time
        # in time.sleep(0.2) between polls — patch it out so the test stays
        # in milliseconds even on the (rare) path where polling iterates.
        import yedi_benchmark.yedi_env as yedi_env_mod
        monkeypatch.setattr(yedi_env_mod.time, "sleep", lambda *_a, **_k: None)
        return sent

    def test_perfect_memory_omitted_by_default(self, monkeypatch):
        # Canonical-benchmark behaviour: no perfect_memory key in start_game,
        # so the bridge keeps the default false and Memory mode masking stays
        # active.
        env = _make_reset_env({"modes": {"number": "add", "memory": "every_action"}})
        sent = self._patch_reset(env, monkeypatch)

        env.reset()

        start = next(c for c in sent if c.get("type") == "start_game")
        assert "perfect_memory" not in start
        assert start["mode_memory"] == "every_action"

    def test_perfect_memory_threaded_when_enabled(self, monkeypatch):
        # Per-run ablation: when game_config["perfect_memory"] is True, the
        # env must include perfect_memory:true in the start_game command so
        # the bridge stops masking hidden card values.
        env = _make_reset_env({
            "modes": {"number": "add", "memory": "every_action"},
            "perfect_memory": True,
        })
        sent = self._patch_reset(env, monkeypatch)

        env.reset()

        start = next(c for c in sent if c.get("type") == "start_game")
        assert start["perfect_memory"] is True
