"""Pydantic models for the registry layer.

Design notes:
  - AgentConfig stores an env var NAME, never the API key value itself.
  - Prompt is structured: core_rules (free text) + dimension_rules (per-mode dict).
  - RunRecord SNAPSHOTS the agent and prompt at create time. Editing the
    registry later does not retro-modify completed runs. This is the foundation
    of meaningful bookkeeping.
  - All datetimes are ISO 8601 strings for JSON serialization simplicity.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentMode(str, Enum):
    """Observation + memory combination used by an LLM agent during a run.

    Memory dimension (a/b/c):
      a — stateless: each step is a fresh API call, no history.
      b — conversational: every previous full state + assistant action is kept
          in the running message list (high token cost).
      c — compact: a one-line "trail entry" per past step is kept locally and
          prefixed to the current state. The current step is still a full
          dump; only the history is compressed. The format is documented in
          the system prompt so the model can read it.
    """
    METADATA_STATELESS = "metadata-a"
    METADATA_CONVERSATIONAL = "metadata-b"
    METADATA_COMPACT = "metadata-c"
    VISION_STATELESS = "vision-a"
    VISION_CONVERSATIONAL = "vision-b"
    VISION_COMPACT = "vision-c"

    @property
    def use_screenshot(self) -> bool:
        return self.value.startswith("vision")

    @property
    def is_conversational(self) -> bool:
        return self.value.endswith("-b")

    @property
    def is_compact(self) -> bool:
        return self.value.endswith("-c")

    @property
    def memory_label(self) -> str:
        """'stateless' | 'conversational' | 'compact' — used by LLMAgent."""
        suffix = self.value.split("-")[-1]
        return {"a": "stateless", "b": "conversational", "c": "compact"}[suffix]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ──────────────────────────────────────────────────────────────────────────────
# AgentConfig
# ──────────────────────────────────────────────────────────────────────────────


class AgentConfig(BaseModel):
    """Definition of a benchmark agent. Stored in agents.json."""

    id: str = Field(default_factory=lambda: _new_id("agent"))
    name: str  # human label, e.g. "Claude Sonnet 4.5"
    provider: str  # one of providers.SUPPORTED_PROVIDERS
    model: str  # LiteLLM-compatible model string, or "" for random
    api_key_env: Optional[str] = None  # env var NAME, never the value
    base_url: Optional[str] = None  # for openai-compatible custom endpoints
    max_tokens: int = 512
    supports_vision: bool = False
    # Ollama-specific: override the backend's default context window. The
    # Ollama default is 4096 tokens, which truncates our 18 KB system prompt
    # silently and causes "model runner stopped" crashes on vision requests.
    # Setting this to e.g. 16384 allocates a larger KV cache at load time.
    # Ignored for non-Ollama providers.
    num_ctx: Optional[int] = None
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

    @field_validator("name")
    @classmethod
    def _name_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v.strip()

    @field_validator("provider")
    @classmethod
    def _provider_valid(cls, v: str) -> str:
        # Imported here to avoid circular import at module load
        from ..providers.registry import SUPPORTED_PROVIDERS
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(f"provider must be one of {SUPPORTED_PROVIDERS}")
        return v


# ──────────────────────────────────────────────────────────────────────────────
# Prompt
# ──────────────────────────────────────────────────────────────────────────────


class Prompt(BaseModel):
    """Versioned prompt template. Stored in prompts.json.

    The Yedi LLMAgent assembles the final system prompt from:
      1. core_rules (universal game-mechanics text)
      2. dimension_rules entries for each ACTIVE mode in the current game
      3. response format footer

    dimension_rules is keyed by "<dimension_field>:<mode_value>", e.g.
    "number:add", "color:add", "memory:every action".
    """

    id: str = Field(default_factory=lambda: _new_id("prompt"))
    name: str
    version: int = 1
    core_rules: str
    dimension_rules: dict[str, str] = Field(default_factory=dict)
    is_active: bool = False
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

    @field_validator("name")
    @classmethod
    def _name_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v.strip()

    @field_validator("core_rules")
    @classmethod
    def _core_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("core_rules must be non-empty")
        return v


# ──────────────────────────────────────────────────────────────────────────────
# Episode + run records
# ──────────────────────────────────────────────────────────────────────────────


class EpisodeResult(BaseModel):
    """Result of one episode of one game config."""

    episode_idx: int
    max_mana: float
    surplus: float = 0.0  # max_mana - initial_mana (200); the actual score
    total_reward: float
    steps: int
    game_over: bool
    episode_log_path: Optional[str] = None  # link to logs/episode_*/ if any
    started_at: str = Field(default_factory=_utcnow_iso)
    finished_at: Optional[str] = None
    # Per-episode diagnostics for benchmark quality analysis. None when the
    # runner was invoked without diagnostic tracking (backwards compat).
    diagnostics: Optional[dict] = None


class ConfigResult(BaseModel):
    """Aggregate of all episodes for a single game config within a run."""

    config_name: str
    modes: dict[str, str]  # raw mode dict, e.g. {"number": "add"}
    episodes: list[EpisodeResult] = Field(default_factory=list)

    # Aggregates (recomputed by the runner; safe to leave empty until episodes finish)
    mean_max_mana: float = 0.0
    std_max_mana: float = 0.0
    best_max_mana: float = 0.0
    # Surplus = max_mana - initial_mana (200). This is the primary score.
    mean_surplus: float = 0.0
    std_surplus: float = 0.0
    best_surplus: float = 0.0


class RunRecord(BaseModel):
    """Top-level benchmark run record. Stored as logs/runs/{id}.json."""

    id: str = Field(default_factory=lambda: _new_id("run"))
    status: RunStatus = RunStatus.PENDING
    started_at: str = Field(default_factory=_utcnow_iso)
    finished_at: Optional[str] = None

    # SNAPSHOTS (frozen at create time, not foreign keys).
    # Stored as plain dicts so the file is self-contained and forward-compatible.
    agent_snapshot: dict
    prompt_snapshot: Optional[dict] = None  # None for random agents

    # Run configuration
    configs: list[str]  # config names, e.g. ["easy_math_add", "easy_visual_add"]
    episodes_per_config: int
    max_steps: int
    mode: AgentMode

    # Per-run ablations. Snapshotted so an old record stays interpretable
    # even after we change the defaults. Both default to False (canonical
    # benchmark) for backwards compatibility with records written before the
    # flags existed.
    show_merge_previews: bool = False
    perfect_memory: bool = False
    workers: int = 1  # parallel worker servers used for this run

    # Per-config results
    results: dict[str, ConfigResult] = Field(default_factory=dict)

    # Optional error message if status == FAILED
    error: Optional[str] = None

    # Per-episode errors recorded by the runner when an individual episode
    # crashed (e.g. bridge timeout) but the run as a whole continued. Each
    # entry: {config, episode_idx, error, ts}. Empty for clean runs.
    episode_errors: list[dict] = Field(default_factory=list)

    def episodes_done(self) -> int:
        return sum(len(r.episodes) for r in self.results.values())

    def episodes_total(self) -> int:
        return len(self.configs) * self.episodes_per_config
