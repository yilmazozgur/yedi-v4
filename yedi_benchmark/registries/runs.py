"""Run registry — file-per-record storage for benchmark RunRecords.

Storage: <runs_dir>/{run_id}.json (one file per run)

Why one-file-per-run instead of a single index?
  - Atomic writes: each run's progress is persisted independently.
  - No lock contention between concurrent runs (though we currently allow only
    one at a time, this future-proofs us).
  - Easy to inspect, copy, or delete a single run by hand.

The registry supports:
  - create(): freezes agent + prompt snapshots and writes the initial record.
  - get(), list(): read records.
  - update_status(), set_error(): lifecycle transitions.
  - append_episode(): write a single episode result and refresh aggregates.
  - delete(): remove a run.
"""

from __future__ import annotations

import json
import logging
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    AgentConfig,
    AgentMode,
    ConfigResult,
    EpisodeResult,
    Prompt,
    RunRecord,
    RunStatus,
)
from .paths import get_runs_dir


logger = logging.getLogger("registries.runs")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRegistryError(Exception):
    """Raised on registry errors."""


class RunRegistry:
    """File-per-record store for RunRecord objects.

    Thread-safe via a single lock around all read/write operations. The lock
    is coarse but acceptable: writes are infrequent (once per episode) and
    runs are sequential by design.
    """

    def __init__(self, runs_dir: Optional[Path] = None):
        self._runs_dir = Path(runs_dir) if runs_dir else get_runs_dir()
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ----- internal -----

    def _path_for(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _write(self, record: RunRecord) -> None:
        path = self._path_for(record.id)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))
        tmp.replace(path)

    # ----- public API -----

    def create(
        self,
        agent: AgentConfig,
        prompt: Optional[Prompt],
        configs: list[str],
        episodes_per_config: int,
        max_steps: int,
        mode: AgentMode,
        config_modes: Optional[dict[str, dict[str, str]]] = None,
        show_merge_previews: bool = False,
        perfect_memory: bool = False,
    ) -> RunRecord:
        """Create a new RunRecord with frozen agent + prompt snapshots.

        Args:
            agent: AgentConfig instance to snapshot.
            prompt: Prompt instance to snapshot, or None for non-LLM agents.
            configs: list of game config names (must be in benchmark_configs).
            episodes_per_config: how many episodes per config.
            max_steps: episode step cap.
            mode: AgentMode (metadata-a/b, vision-a/b).
            config_modes: optional dict mapping config_name to its mode dict.
                If not provided, ConfigResult.modes will be empty until first
                episode is appended (the runner can backfill it).
            show_merge_previews: per-run ablation — when True, the LLM agent
                receives the bridge's pre-computed merge previews in its
                state description. Default False (canonical benchmark).
            perfect_memory: per-run ablation — when True, the bridge ships
                hidden card values + previews regardless of Memory mode.
                Default False (Memory dimension is real).
        """
        if not configs:
            raise RunRegistryError("configs must be non-empty")
        if episodes_per_config < 1:
            raise RunRegistryError("episodes_per_config must be ≥ 1")

        with self._lock:
            record = RunRecord(
                status=RunStatus.PENDING,
                agent_snapshot=agent.model_dump(),
                prompt_snapshot=prompt.model_dump() if prompt else None,
                configs=list(configs),
                episodes_per_config=episodes_per_config,
                max_steps=max_steps,
                mode=mode,
                show_merge_previews=show_merge_previews,
                perfect_memory=perfect_memory,
                results={
                    name: ConfigResult(
                        config_name=name,
                        modes=(config_modes or {}).get(name, {}),
                    )
                    for name in configs
                },
            )
            self._write(record)
            logger.info(
                "created run %s (agent=%s, configs=%d, episodes=%d, "
                "show_previews=%s, perfect_memory=%s)",
                record.id, agent.name, len(configs), episodes_per_config,
                show_merge_previews, perfect_memory,
            )
            return record

    def get(self, run_id: str) -> RunRecord:
        with self._lock:
            path = self._path_for(run_id)
            if not path.exists():
                raise RunRegistryError(f"run not found: {run_id}")
            with path.open("r", encoding="utf-8") as f:
                return RunRecord.model_validate_json(f.read())

    def list(self, status: Optional[RunStatus] = None) -> list[RunRecord]:
        """List all runs, optionally filtered by status. Newest first."""
        with self._lock:
            records: list[RunRecord] = []
            for path in self._runs_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        records.append(RunRecord.model_validate_json(f.read()))
                except Exception as e:
                    logger.warning("skipping malformed run file %s: %s", path, e)
            if status is not None:
                records = [r for r in records if r.status == status]
            records.sort(key=lambda r: r.started_at, reverse=True)
            return records

    def delete(self, run_id: str) -> None:
        with self._lock:
            path = self._path_for(run_id)
            if not path.exists():
                raise RunRegistryError(f"run not found: {run_id}")
            path.unlink()

    def reconcile_orphans(self, reason: Optional[str] = None) -> list[str]:
        """Mark any PENDING/RUNNING records on disk as FAILED.

        Called at server startup. After a crash or restart, the worker thread
        that owned an in-flight run is gone, but the on-disk record still says
        ``status: running`` — that strands the run in the UI (Cancel returns
        404 because the executor isn't tracking it, and Delete is hidden by
        the row template until the run leaves the running state).

        Returns the list of run ids that were reconciled, for logging.
        """
        msg = reason or "orphaned by server restart (worker thread no longer alive)"
        reconciled: list[str] = []
        with self._lock:
            for path in self._runs_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        record = RunRecord.model_validate_json(f.read())
                except Exception as e:
                    logger.warning("skipping malformed run file %s: %s", path, e)
                    continue
                if record.status not in (RunStatus.PENDING, RunStatus.RUNNING):
                    continue
                record.status = RunStatus.FAILED
                record.error = msg
                record.finished_at = _now_iso()
                self._write(record)
                reconciled.append(record.id)
                logger.warning("reconciled orphan run %s -> FAILED", record.id)
        return reconciled

    # ----- lifecycle transitions -----

    def update_status(self, run_id: str, status: RunStatus) -> RunRecord:
        with self._lock:
            record = self.get(run_id)
            record.status = status
            if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                record.finished_at = _now_iso()
            self._write(record)
            return record

    def set_error(self, run_id: str, error: str) -> RunRecord:
        with self._lock:
            record = self.get(run_id)
            record.status = RunStatus.FAILED
            record.error = error
            record.finished_at = _now_iso()
            self._write(record)
            return record

    def record_episode_error(
        self,
        run_id: str,
        config_name: str,
        episode_idx: int,
        error: str,
    ) -> RunRecord:
        """Record a per-episode failure without aborting the run.

        Used by the runner when an individual episode crashes (e.g. the
        WebSocket bridge to the browser dies mid-step) but we want to keep
        going with the next episode/config instead of marking the whole run
        FAILED. The episode is NOT appended to ConfigResult.episodes — only
        successful episodes count toward the per-config aggregates — but the
        error is logged on the run record so the dashboard can surface it.
        """
        with self._lock:
            record = self.get(run_id)
            record.episode_errors.append({
                "config": config_name,
                "episode_idx": episode_idx,
                "error": error,
                "ts": _now_iso(),
            })
            self._write(record)
            return record

    def append_episode(
        self,
        run_id: str,
        config_name: str,
        episode: EpisodeResult,
    ) -> RunRecord:
        """Append a single episode result and recompute aggregates for that config."""
        with self._lock:
            record = self.get(run_id)
            if config_name not in record.results:
                # Lazily create if missing (defensive — create() should have seeded)
                record.results[config_name] = ConfigResult(
                    config_name=config_name, modes={},
                )
            cfg = record.results[config_name]
            cfg.episodes.append(episode)
            self._recompute_aggregates(cfg)
            self._write(record)
            return record

    @staticmethod
    def _recompute_aggregates(cfg: ConfigResult) -> None:
        manas = [e.max_mana for e in cfg.episodes]
        surpluses = [e.surplus for e in cfg.episodes]
        if not manas:
            cfg.mean_max_mana = cfg.std_max_mana = cfg.best_max_mana = 0.0
            cfg.mean_surplus = cfg.std_surplus = cfg.best_surplus = 0.0
            return
        cfg.mean_max_mana = float(sum(manas) / len(manas))
        cfg.std_max_mana = float(statistics.pstdev(manas)) if len(manas) > 1 else 0.0
        cfg.best_max_mana = float(max(manas))
        cfg.mean_surplus = float(sum(surpluses) / len(surpluses))
        cfg.std_surplus = float(statistics.pstdev(surpluses)) if len(surpluses) > 1 else 0.0
        cfg.best_surplus = float(max(surpluses))
