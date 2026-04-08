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


class TestYediEnvResetCommand:
    def _patch_reset(self, env, monkeypatch):
        """Capture every _send_command call into a list and return canned state."""
        sent: list[dict] = []

        def fake_send(command, timeout=30.0):
            sent.append(command)
            # Reset() expects the second call (get_state) to return a state
            # dict with at least mana + slots so _state_to_obs doesn't blow up.
            return {
                "type": "state", "mana": 200, "mana_max": 200,
                "timer_remaining": 0.0, "beat_phase": 0.0,
                "slots": [{"occupied": False} for _ in range(7)],
                "valid_actions": [0, 37], "seq": 1,
            }

        monkeypatch.setattr(env, "_send_command", fake_send)
        # The real reset() does time.sleep(3.0) between start_game and
        # get_state to wait for the scene to load — patch it out so the
        # test runs in milliseconds, not seconds.
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
