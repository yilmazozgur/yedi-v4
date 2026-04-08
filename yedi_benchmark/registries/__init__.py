"""Registries for agents, prompts, and benchmark runs.

Each registry is a JSON-backed CRUD store. Files live under
yedi_benchmark/data/ (gitignored). The registries are the single source of
truth used by both the CLI runner and the web UI.

Public API:
  from yedi_benchmark.registries import (
      AgentConfig, Prompt, RunRecord, EpisodeResult, ConfigResult,
      AgentRegistry, PromptRegistry, RunRegistry,
      get_data_dir,
  )
"""

from .models import (
    AgentConfig,
    ConfigResult,
    EpisodeResult,
    Prompt,
    RunRecord,
    RunStatus,
    AgentMode,
)
from .paths import get_data_dir, get_runs_dir
from .agents import AgentRegistry
from .prompts import PromptRegistry
from .runs import RunRegistry

__all__ = [
    "AgentConfig",
    "ConfigResult",
    "EpisodeResult",
    "Prompt",
    "RunRecord",
    "RunStatus",
    "AgentMode",
    "AgentRegistry",
    "PromptRegistry",
    "RunRegistry",
    "get_data_dir",
    "get_runs_dir",
]
