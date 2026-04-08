"""In-memory live trace of LLM exchanges during a benchmark run.

The dashboard's Run page polls this so the user can watch the model think:
each entry holds the user message that was sent to the LLM, the raw response,
the parsed action, and timing. System prompts are stored once per config to
keep poll payloads small.

Design notes:
  - Bounded per-run buffer (deque) so a long run can't OOM the process.
  - Bounded number of runs in the store (LRU eviction) for the same reason.
  - Cursor-based polling — clients pass ``?since=N`` and get only new entries.
  - Thread-safe: the runner thread writes, the API thread reads.
  - This is a *live* surface, not the source of truth. The persistent record
    of a run still lives in RunRegistry. Trace entries are dropped when the
    server restarts.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional


# Per-run buffer cap. ~500 entries × ~2KB each ≈ 1MB max per active run.
MAX_ENTRIES_PER_RUN = 500

# Total runs we keep traces for at once (LRU). Older runs are dropped from
# memory; their persistent RunRecord is unaffected.
MAX_RUNS_IN_STORE = 20


class RunTrace:
    """Bounded ring buffer of LLM exchanges for one run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._entries: deque = deque(maxlen=MAX_ENTRIES_PER_RUN)
        self._cursor = 0  # monotonic; entries get assigned an id from this
        self._system_prompts: dict[str, str] = {}  # config_name -> system prompt
        self._lock = threading.Lock()

    def record(
        self,
        *,
        config: Optional[str],
        episode: int,
        step: int,
        user_text: str,
        response: str,
        action: Optional[int],
        latency_ms: Optional[float],
        error: Optional[str] = None,
    ) -> int:
        """Append a new exchange. Returns the entry's monotonic id."""
        with self._lock:
            self._cursor += 1
            entry = {
                "id": self._cursor,
                "ts": time.time(),
                "config": config,
                "episode": episode,
                "step": step,
                "user_text": user_text,
                "response": response,
                "action": action,
                "latency_ms": latency_ms,
                "error": error,
            }
            self._entries.append(entry)
            return self._cursor

    def set_system_prompt(self, config_name: str, prompt_text: str) -> None:
        with self._lock:
            self._system_prompts[config_name] = prompt_text

    def snapshot(self, since_id: int = 0) -> dict:
        """Return all entries with id > since_id, plus system-prompt context."""
        with self._lock:
            entries = [e for e in self._entries if e["id"] > since_id]
            return {
                "run_id": self.run_id,
                "cursor": self._cursor,
                "system_prompts": dict(self._system_prompts),
                "entries": entries,
                "dropped": self._cursor - (self._entries[0]["id"] - 1) > len(self._entries)
                if self._entries else False,
            }


class RunTraceStore:
    """LRU dict of RunTrace, keyed by run_id."""

    def __init__(self) -> None:
        self._traces: dict[str, RunTrace] = {}
        self._order: deque = deque()
        self._lock = threading.Lock()

    def get_or_create(self, run_id: str) -> RunTrace:
        with self._lock:
            if run_id in self._traces:
                return self._traces[run_id]
            # Evict oldest if at capacity
            while len(self._order) >= MAX_RUNS_IN_STORE:
                old = self._order.popleft()
                self._traces.pop(old, None)
            t = RunTrace(run_id)
            self._traces[run_id] = t
            self._order.append(run_id)
            return t

    def get(self, run_id: str) -> Optional[RunTrace]:
        with self._lock:
            return self._traces.get(run_id)

    def drop(self, run_id: str) -> None:
        with self._lock:
            self._traces.pop(run_id, None)
            try:
                self._order.remove(run_id)
            except ValueError:
                pass

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()
            self._order.clear()


# Process-wide singleton.
_singleton: Optional[RunTraceStore] = None
_singleton_lock = threading.Lock()


def get_run_trace_store() -> RunTraceStore:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = RunTraceStore()
    return _singleton


def reset_run_trace_store() -> None:
    """Used by tests for clean isolation between cases."""
    global _singleton
    with _singleton_lock:
        _singleton = RunTraceStore()
