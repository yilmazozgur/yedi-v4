"""Parallel benchmark runner — dispatch configs to N worker servers.

Spawns N server+browser pairs via WorkerPool, distributes config items
across worker threads via a shared queue, and merges results into a single
RunRecord.  Called from ``run_benchmark_with_registry(..., workers=N)`` when
N > 1.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

from .benchmark_runner import (
    RunCancelled,
    _ConfigStats,
    _finalize_run,
    _run_single_config,
)
from .replay_logger import ReplayLogger
from .worker_pool import WorkerPool

logger = logging.getLogger("yedi_benchmark.parallel_runner")


def run_benchmark_parallel(
    record,
    config_modes: dict,
    agent_cfg,
    prompt,
    mode_enum,
    env_cls,
    replay_logger: ReplayLogger,
    trace,
    rr,
    episodes_per_config: int,
    max_steps: int,
    cancel_event,
    show_merge_previews: bool,
    perfect_memory: bool,
    is_llm: bool,
    n_workers: int,
) -> "RunRecord":
    """Run a benchmark using N parallel worker servers.

    Each worker server runs in its own subprocess and gets its own browser
    tab. Configs are dispatched from a shared queue so faster workers
    automatically pick up more work.
    """
    from .registries import RunStatus
    from .providers.base import ProviderCancelled

    # Cap workers at the number of configs — no point having idle workers.
    actual_workers = min(n_workers, len(config_modes))
    stats = _ConfigStats()

    # Build a work queue of (config_name, modes_dict) tuples.
    work_queue: queue.Queue = queue.Queue()
    for cfg_name, modes in config_modes.items():
        work_queue.put((cfg_name, modes))

    # Accumulate exceptions from worker threads.
    worker_errors: list[Exception] = []
    errors_lock = threading.Lock()

    def _worker_loop(worker_url: str, worker_idx: int):
        """Pull configs from the queue and run them on this worker's server."""
        worker_replay = ReplayLogger(log_dir=str(replay_logger.log_dir))
        while True:
            # Check cancel before pulling next config.
            if cancel_event is not None and cancel_event.is_set():
                return

            try:
                cfg_name, modes = work_queue.get_nowait()
            except queue.Empty:
                return  # No more work.

            try:
                _run_single_config(
                    cfg_name=cfg_name,
                    modes=modes,
                    agent_cfg=agent_cfg,
                    prompt=prompt,
                    mode_enum=mode_enum,
                    env_cls=env_cls,
                    server_url=worker_url,
                    replay_logger=worker_replay,
                    trace=trace,
                    record_id=record.id,
                    rr=rr,
                    episodes_per_config=episodes_per_config,
                    max_steps=max_steps,
                    cancel_event=cancel_event,
                    show_merge_previews=show_merge_previews,
                    perfect_memory=perfect_memory,
                    is_llm=is_llm,
                    stats=stats,
                    # Hidden browser tabs can be throttled by Chrome
                    # (rAF drops to ~1 Hz) despite anti-throttle flags.
                    # The higher timeout prevents command timeouts from
                    # cascading into BridgeDisconnectedError + scene
                    # reload ("game keeps restarting").
                    command_timeout=120.0,
                )
            except RunCancelled:
                return
            except Exception as e:
                logger.warning(
                    "Worker %d failed on config %s: %s",
                    worker_idx, cfg_name, e,
                )
                with errors_lock:
                    worker_errors.append(e)
                # Don't abort the whole pool on one config failure —
                # let the worker pick up the next config.

    pool = WorkerPool(n_workers=actual_workers)
    try:
        logger.info(
            "Starting %d parallel workers for %d configs",
            actual_workers, len(config_modes),
        )
        pool.start_all()

        urls = pool.ws_agent_urls
        threads: list[threading.Thread] = []
        for i, url in enumerate(urls):
            t = threading.Thread(
                target=_worker_loop,
                args=(url, i),
                name=f"yedi-worker-{i}",
                daemon=True,
            )
            threads.append(t)
            t.start()

        # Wait for all threads to finish.
        for t in threads:
            t.join()

    except Exception as e:
        logger.error("Parallel runner failed: %s", e, exc_info=True)
        # If it's a cancel, let it propagate for proper status handling.
        if isinstance(e, (RunCancelled, ProviderCancelled)):
            rr.update_status(record.id, RunStatus.CANCELLED)
            return rr.get(record.id)
        rr.set_error(record.id, str(e))
        raise
    finally:
        pool.stop_all()

    # Handle cancellation detected by worker threads.
    if cancel_event is not None and cancel_event.is_set():
        logger.info(f"Run {record.id} CANCELLED")
        rr.update_status(record.id, RunStatus.CANCELLED)
        return rr.get(record.id)

    # If all workers errored with provider cancellation, treat as cancel.
    if worker_errors:
        provider_cancels = [
            e for e in worker_errors if isinstance(e, ProviderCancelled)
        ]
        if len(provider_cancels) == len(worker_errors):
            rr.update_status(record.id, RunStatus.CANCELLED)
            return rr.get(record.id)

    return _finalize_run(record, rr, stats)
