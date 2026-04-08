"""Live state of the Python <-> browser WebSocket bridge.

The dashboard needs to know whether a browser tab is currently connected to
``/ws/game`` so it can:
  1. Show a "game connected/disconnected" pill in the sidebar.
  2. Refuse to launch a benchmark run when there's no game on the other end
     (otherwise episodes silently complete with garbage observations).

This module is the single source of truth. ``gym_server.py`` updates it from
the WebSocket handlers; the API routes read it via the dependency below.
Tests can override the dependency to simulate a connected game without
actually opening a WebSocket.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class BridgeSnapshot:
    """JSON-serializable snapshot of the bridge state, returned by the API."""
    game_connected: bool
    agent_connected: bool
    game_connected_at: float | None  # unix epoch seconds
    agent_connected_at: float | None


class BridgeStatus:
    """Thread-safe live status of the WebSocket bridge.

    There is exactly one instance per process, exposed via
    ``get_bridge_status()``. The WebSocket handlers in gym_server.py call
    ``mark_game_connected()`` / ``mark_game_disconnected()`` (and the same for
    the agent side) as connections come and go.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._game_connected = False
        self._agent_connected = False
        self._game_connected_at: float | None = None
        self._agent_connected_at: float | None = None

    # ── mutators (called from gym_server WebSocket handlers) ──

    def mark_game_connected(self) -> None:
        with self._lock:
            self._game_connected = True
            self._game_connected_at = time.time()

    def mark_game_disconnected(self) -> None:
        with self._lock:
            self._game_connected = False
            self._game_connected_at = None

    def mark_agent_connected(self) -> None:
        with self._lock:
            self._agent_connected = True
            self._agent_connected_at = time.time()

    def mark_agent_disconnected(self) -> None:
        with self._lock:
            self._agent_connected = False
            self._agent_connected_at = None

    # ── readers (called from API routes) ──

    def is_game_connected(self) -> bool:
        with self._lock:
            return self._game_connected

    def is_agent_connected(self) -> bool:
        with self._lock:
            return self._agent_connected

    def snapshot(self) -> BridgeSnapshot:
        with self._lock:
            return BridgeSnapshot(
                game_connected=self._game_connected,
                agent_connected=self._agent_connected,
                game_connected_at=self._game_connected_at,
                agent_connected_at=self._agent_connected_at,
            )


# Process-wide singleton.
_singleton: BridgeStatus | None = None
_singleton_lock = threading.Lock()


def get_bridge_status() -> BridgeStatus:
    """FastAPI dependency injector — also usable directly from gym_server."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = BridgeStatus()
    return _singleton


def reset_bridge_status() -> None:
    """Replace the singleton — used by tests for clean isolation."""
    global _singleton
    with _singleton_lock:
        _singleton = BridgeStatus()
