"""Unit tests for the BridgeStatus singleton."""

from __future__ import annotations

import threading
import time

from yedi_benchmark.bridge_status import (
    BridgeStatus,
    get_bridge_status,
    reset_bridge_status,
)


class TestBridgeStatus:
    def test_starts_disconnected(self):
        b = BridgeStatus()
        assert b.is_game_connected() is False
        assert b.is_agent_connected() is False
        snap = b.snapshot()
        assert snap.game_connected is False
        assert snap.agent_connected is False
        assert snap.game_connected_at is None
        assert snap.agent_connected_at is None

    def test_mark_game_connected(self):
        b = BridgeStatus()
        before = time.time()
        b.mark_game_connected()
        snap = b.snapshot()
        assert snap.game_connected is True
        assert snap.game_connected_at is not None
        assert snap.game_connected_at >= before

    def test_mark_game_disconnected_clears_timestamp(self):
        b = BridgeStatus()
        b.mark_game_connected()
        b.mark_game_disconnected()
        snap = b.snapshot()
        assert snap.game_connected is False
        assert snap.game_connected_at is None

    def test_agent_connection_independent_of_game(self):
        b = BridgeStatus()
        b.mark_agent_connected()
        assert b.is_agent_connected() is True
        assert b.is_game_connected() is False

        b.mark_game_connected()
        assert b.is_agent_connected() is True
        assert b.is_game_connected() is True

        b.mark_agent_disconnected()
        assert b.is_agent_connected() is False
        assert b.is_game_connected() is True

    def test_snapshot_is_a_point_in_time_copy(self):
        b = BridgeStatus()
        b.mark_game_connected()
        snap = b.snapshot()
        b.mark_game_disconnected()
        # The earlier snapshot is unaffected by later mutations
        assert snap.game_connected is True


class TestSingleton:
    def test_get_bridge_status_returns_same_instance(self):
        reset_bridge_status()
        a = get_bridge_status()
        b = get_bridge_status()
        assert a is b

    def test_reset_replaces_singleton(self):
        a = get_bridge_status()
        a.mark_game_connected()
        reset_bridge_status()
        b = get_bridge_status()
        assert a is not b
        assert b.is_game_connected() is False


class TestThreadSafety:
    def test_concurrent_marks_do_not_corrupt_state(self):
        b = BridgeStatus()
        stop = threading.Event()

        def flapper():
            while not stop.is_set():
                b.mark_game_connected()
                b.mark_game_disconnected()

        threads = [threading.Thread(target=flapper) for _ in range(4)]
        for t in threads:
            t.start()

        # Hammer the reader for a bit — this would deadlock or crash without
        # proper locking
        for _ in range(2000):
            b.snapshot()

        stop.set()
        for t in threads:
            t.join(timeout=2)
            assert not t.is_alive()
