"""Request/response schemas for the API layer.

We re-use the registry Pydantic models (AgentConfig, Prompt, RunRecord) for
responses since they already serialize cleanly to JSON. The schemas in this
file are the *write* shapes — what the UI POSTs/PUTs — which differ from the
storage shapes by stripping server-managed fields like id and timestamps.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ..registries.models import AgentMode


# ──────────────────────────────────────────────────────────────────────────────
# Agents
# ──────────────────────────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    name: str
    provider: str
    model: str
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 512
    supports_vision: bool = False


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    supports_vision: Optional[bool] = None


class AgentTestResult(BaseModel):
    success: bool
    message: str


class ProviderInfo(BaseModel):
    """Read-only metadata used by the Add-Agent form in the UI."""
    providers: list[str]
    default_models: dict[str, list[str]]
    default_api_key_envs: dict[str, str]


# ──────────────────────────────────────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────────────────────────────────────


class PromptCreate(BaseModel):
    name: str
    core_rules: str
    dimension_rules: dict[str, str] = Field(default_factory=dict)
    version: int = 1


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    core_rules: Optional[str] = None
    dimension_rules: Optional[dict[str, str]] = None
    version: Optional[int] = None


class PromptCloneRequest(BaseModel):
    new_name: str


# ──────────────────────────────────────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────────────────────────────────────


class RunCreate(BaseModel):
    """POST /api/runs body — kicks off a benchmark run."""
    agent_id: str
    prompt_id: Optional[str] = None  # defaults to active prompt at start time
    mode: AgentMode = AgentMode.METADATA_CONVERSATIONAL
    configs: list[str]
    episodes_per_config: int = 3
    max_steps: int = 100
    server_url: str = "ws://localhost:8000/ws/agent"
    log_dir: str = "./logs"
    # Per-run ablations. Both default OFF so the canonical benchmark stays
    # honest — flip them on to compare an "assisted" or "perfect-memory" run
    # against the baseline.
    show_merge_previews: bool = False  # render bridge merge_previews to LLMs
    perfect_memory: bool = False        # disable Memory dimension masking


class RunActiveStatus(BaseModel):
    """Lightweight current-run snapshot for the UI poll loop."""
    active: bool
    run_id: Optional[str] = None
    status: Optional[str] = None
    episodes_done: int = 0
    episodes_total: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Bridge
# ──────────────────────────────────────────────────────────────────────────────


class BridgeStatusResponse(BaseModel):
    """Live state of the Python <-> browser WebSocket bridge."""
    game_connected: bool
    agent_connected: bool
    game_connected_at: Optional[float] = None
    agent_connected_at: Optional[float] = None
