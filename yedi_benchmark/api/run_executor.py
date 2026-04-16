"""Background-thread benchmark runner with single-run lock + cancellation.

Why a thread (not asyncio): the benchmark runner uses synchronous WebSocket
I/O via YediEnv, makes blocking HTTP calls to LLM providers, and must keep
running long after the API request that started it has returned. A daemon
thread is the simplest fit and survives the request/response cycle.

Why single-run: the WebSocket bridge to the Unity browser instance only
supports one game at a time. Allowing concurrent runs would corrupt state.
The lock is enforced at start time — callers get a 409 if a run is already
in flight.

Lifecycle:
    start(...) -> creates RunRecord (PENDING), kicks off worker thread,
                  returns the record (now RUNNING).
    cancel(run_id) -> sets the cancel_event; the worker checks it between
                      configs and episodes and marks the record CANCELLED.
    get_active() -> snapshot for the UI poll loop.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from ..benchmark_runner import run_benchmark_with_registry
from ..registries import RunRecord, RunRegistry, RunStatus

logger = logging.getLogger("api.run_executor")


class ExecutorBusyError(Exception):
    """A run is already in progress."""


class RunExecutor:
    """Process-wide singleton that owns the worker thread + cancel state."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._cancel_event: Optional[threading.Event] = None
        self._current_run_id: Optional[str] = None

    # ----- public API -----

    def start(
        self,
        run_registry: RunRegistry,
        agent_id: str,
        prompt_id: Optional[str],
        mode: str,
        configs: list[str],
        episodes_per_config: int,
        max_steps: int,
        server_url: str,
        log_dir: str,
        show_merge_previews: bool = False,
        perfect_memory: bool = False,
        workers: int = 1,
    ) -> RunRecord:
        """Start a benchmark run in a background thread.

        Raises:
            ExecutorBusyError: if a run is already in progress.
        """
        with self._lock:
            if self._is_running_locked():
                raise ExecutorBusyError(
                    f"a run is already in progress: {self._current_run_id}"
                )

            cancel_event = threading.Event()

            def _worker():
                try:
                    run_benchmark_with_registry(
                        agent_id=agent_id,
                        prompt_id=prompt_id,
                        mode=mode,
                        config_names=configs,
                        episodes_per_config=episodes_per_config,
                        max_steps=max_steps,
                        server_url=server_url,
                        log_dir=log_dir,
                        cancel_event=cancel_event,
                        show_merge_previews=show_merge_previews,
                        perfect_memory=perfect_memory,
                        workers=workers,
                    )
                except Exception:
                    # Errors are already logged + persisted to the run record
                    # by run_benchmark_with_registry. We swallow here so the
                    # daemon thread exits cleanly.
                    logger.exception("benchmark thread crashed")
                finally:
                    with self._lock:
                        self._thread = None
                        self._cancel_event = None
                        self._current_run_id = None

            # We need to know the run_id BEFORE the worker starts so the API
            # can return it to the caller. The cleanest way is to do the
            # registry create() in this thread (cheap) and pass the existing
            # run_id to the worker. But run_benchmark_with_registry currently
            # creates the record itself. Instead, we lookup the latest run
            # immediately after the worker creates it — using a small handoff
            # primitive: an event the worker sets after registering its run.
            #
            # Simpler: pre-create the run here ourselves, then have the worker
            # call a variant that takes an existing run_id. To avoid bloating
            # run_benchmark_with_registry's API surface again, we instead
            # accept a small race: snapshot the registry's "latest" before
            # starting and after, take the diff. The thread is the only writer
            # at this moment because the lock is held.
            existing_ids = {r.id for r in run_registry.list()}

            self._cancel_event = cancel_event
            self._thread = threading.Thread(
                target=_worker, daemon=True, name=f"yedi-run-{agent_id}"
            )
            self._thread.start()

            # Wait briefly for the worker to create its RunRecord, then read it.
            # Worst case the run id appears within the first ~20ms (just one
            # registry write); we give it 5s before giving up.
            new_record = self._await_new_run(run_registry, existing_ids, timeout=5.0)
            if new_record is None:
                raise RuntimeError("failed to detect new run record after start")
            self._current_run_id = new_record.id
            return new_record

    def cancel(self, run_id: str) -> bool:
        """Request cancellation of the in-flight run.

        Returns True if a cancel was actually requested, False if no matching
        run is in progress.
        """
        with self._lock:
            if not self._is_running_locked() or self._current_run_id != run_id:
                return False
            assert self._cancel_event is not None
            self._cancel_event.set()
            logger.info("cancel requested for %s", run_id)
            return True

    def get_active_run_id(self) -> Optional[str]:
        with self._lock:
            return self._current_run_id if self._is_running_locked() else None

    def is_busy(self) -> bool:
        with self._lock:
            return self._is_running_locked()

    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """Block until the worker thread exits. For tests only.

        Returns True if the thread finished within timeout, False otherwise.
        """
        # Snapshot under lock so we don't race with start().
        with self._lock:
            t = self._thread
        if t is None:
            return True
        t.join(timeout)
        return not t.is_alive()

    # ----- internals -----

    def _is_running_locked(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def _await_new_run(
        run_registry: RunRegistry,
        baseline_ids: set,
        timeout: float,
    ) -> Optional[RunRecord]:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for r in run_registry.list():
                if r.id not in baseline_ids:
                    return r
            time.sleep(0.02)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────

_executor = RunExecutor()


def get_run_executor() -> RunExecutor:
    """FastAPI dependency injector for the singleton executor."""
    return _executor


def reset_run_executor() -> None:
    """Reset the singleton — for tests only."""
    global _executor
    _executor = RunExecutor()
