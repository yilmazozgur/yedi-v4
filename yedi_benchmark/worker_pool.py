"""Manage a pool of N worker servers for parallel benchmark runs.

Usage::

    with WorkerPool(n_workers=3) as pool:
        urls = pool.ws_agent_urls  # ["ws://localhost:8100/ws/agent", ...]
        # dispatch work to these URLs
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .worker_server import WorkerServer, WorkerStartupError

logger = logging.getLogger("yedi_benchmark.worker_pool")

DEFAULT_BASE_PORT = 8100

# Seconds to wait between consecutive browser launches when running many
# workers. Firing 8+ Chrome+SwiftShader instances at the exact same moment
# creates a WASM-compile storm that can push the slowest worker past the
# game-connect timeout. A small stagger spreads the peak without
# meaningfully extending total startup.
_BROWSER_LAUNCH_STAGGER_SECONDS = 2.0


class WorkerPool:
    """Start/stop N isolated worker servers, each with its own browser tab."""

    def __init__(
        self,
        n_workers: int,
        base_port: int = DEFAULT_BASE_PORT,
        build_dir: Optional[str] = None,
    ):
        self.n_workers = n_workers
        self.base_port = base_port
        self._build_dir = build_dir
        self._workers: list[WorkerServer] = []

    @property
    def ws_agent_urls(self) -> list[str]:
        return [w.ws_agent_url for w in self._workers]

    def start_all(
        self,
        server_timeout: float = 30.0,
        browser_timeout: float = 180.0,
    ) -> None:
        """Start all worker servers and their browser tabs.

        Raises WorkerStartupError if any worker fails to start. On failure,
        already-started workers are stopped before the exception propagates.
        """
        try:
            # Phase 1: start all server processes.
            for i in range(self.n_workers):
                port = self.base_port + i
                w = WorkerServer(
                    port,
                    build_dir=self._build_dir,
                    worker_index=i,
                    total_workers=self.n_workers,
                )
                w.start(timeout=server_timeout)
                self._workers.append(w)

            # Phase 2: launch browser tabs with a small stagger so the WASM
            # compile + WebGL init storms don't all land at the same
            # instant. First launch is immediate; subsequent ones wait.
            for i, w in enumerate(self._workers):
                if i > 0 and self.n_workers > 1:
                    time.sleep(_BROWSER_LAUNCH_STAGGER_SECONDS)
                w.launch_browser()

            # Phase 3: wait for all game connections.
            for w in self._workers:
                w.wait_game_connected(timeout=browser_timeout)

            logger.info(
                "WorkerPool: %d workers ready on ports %d-%d",
                self.n_workers,
                self.base_port,
                self.base_port + self.n_workers - 1,
            )
        except Exception:
            self.stop_all()
            raise

    def stop_all(self) -> None:
        """Terminate all workers (idempotent)."""
        for w in self._workers:
            try:
                w.stop()
            except Exception as e:
                logger.warning("Failed to stop worker port %d: %s", w.port, e)
        self._workers.clear()
        logger.info("WorkerPool: all workers stopped")

    # ---- context manager ----

    def __enter__(self) -> "WorkerPool":
        self.start_all()
        return self

    def __exit__(self, *exc) -> None:
        self.stop_all()
