"""Dependency injectors for the API layer.

The registries are heavyweight (they touch disk on first access) and the run
executor is a process singleton. We hand them out via FastAPI's `Depends()`
mechanism so tests can override them with `app.dependency_overrides`.

Usage in a route:
    from .deps import get_agent_registry
    @router.get("/agents")
    def list_agents(reg: AgentRegistry = Depends(get_agent_registry)):
        ...
"""

from __future__ import annotations

from functools import lru_cache

from ..bridge_status import BridgeStatus, get_bridge_status as _get_bridge_status_singleton
from ..registries import AgentRegistry, PromptRegistry, RunRegistry


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return AgentRegistry()


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    return PromptRegistry()


@lru_cache(maxsize=1)
def get_run_registry() -> RunRegistry:
    return RunRegistry()


def get_bridge_status() -> BridgeStatus:
    """FastAPI dependency wrapping the bridge_status singleton.

    Wrapped (rather than re-exported) so tests can override it via
    ``app.dependency_overrides[get_bridge_status] = ...``.
    """
    return _get_bridge_status_singleton()


def reset_registry_singletons() -> None:
    """Clear cached registry singletons. Used by tests when YEDI_DATA_DIR /
    YEDI_RUNS_DIR change between runs."""
    get_agent_registry.cache_clear()
    get_prompt_registry.cache_clear()
    get_run_registry.cache_clear()
