"""/api/agents — CRUD for AgentRegistry, plus the provider metadata endpoint
and a connection test that pings the LLM provider for a chosen agent.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response

from ..providers.registry import (
    DEFAULT_API_KEY_ENVS,
    DEFAULT_BASE_URLS,
    DEFAULT_MODELS,
    SUPPORTED_PROVIDERS,
    create_provider,
)
from ..providers.base import ProviderError
from ..registries import AgentConfig, AgentRegistry
from ..registries.agents import AgentRegistryError
from .deps import get_agent_registry
from .schemas import AgentCreate, AgentUpdate, AgentTestResult, ProviderInfo

logger = logging.getLogger("api.agents")

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/providers", response_model=ProviderInfo)
def list_providers() -> ProviderInfo:
    """Return the curated provider/model menu used by the Add-Agent form."""
    return ProviderInfo(
        providers=SUPPORTED_PROVIDERS,
        default_models=DEFAULT_MODELS,
        default_api_key_envs=DEFAULT_API_KEY_ENVS,
        default_base_urls=DEFAULT_BASE_URLS,
    )


@router.get("", response_model=list[AgentConfig])
def list_agents(reg: AgentRegistry = Depends(get_agent_registry)) -> list[AgentConfig]:
    return reg.list()


@router.post("", response_model=AgentConfig, status_code=201)
def create_agent(
    body: AgentCreate,
    reg: AgentRegistry = Depends(get_agent_registry),
) -> AgentConfig:
    try:
        new = AgentConfig(**body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    try:
        return reg.create(new)
    except AgentRegistryError as e:
        raise HTTPException(409, str(e))


@router.get("/{agent_id}", response_model=AgentConfig)
def get_agent(
    agent_id: str,
    reg: AgentRegistry = Depends(get_agent_registry),
) -> AgentConfig:
    try:
        return reg.get(agent_id)
    except AgentRegistryError as e:
        raise HTTPException(404, str(e))


@router.put("/{agent_id}", response_model=AgentConfig)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    reg: AgentRegistry = Depends(get_agent_registry),
) -> AgentConfig:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        return reg.update(agent_id, **fields)
    except AgentRegistryError as e:
        msg = str(e)
        status = 404 if "not found" in msg else 409
        raise HTTPException(status, msg)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{agent_id}", status_code=204, response_class=Response)
def delete_agent(
    agent_id: str,
    reg: AgentRegistry = Depends(get_agent_registry),
) -> Response:
    try:
        reg.delete(agent_id)
    except AgentRegistryError as e:
        raise HTTPException(404, str(e))
    return Response(status_code=204)


@router.post("/{agent_id}/test", response_model=AgentTestResult)
def test_agent(
    agent_id: str,
    reg: AgentRegistry = Depends(get_agent_registry),
) -> AgentTestResult:
    """Send a tiny ping through the agent's provider to verify credentials."""
    try:
        agent = reg.get(agent_id)
    except AgentRegistryError as e:
        raise HTTPException(404, str(e))

    if agent.provider == "random":
        return AgentTestResult(success=True, message="Random agent (no provider to test)")
    if agent.provider == "greedy":
        return AgentTestResult(success=True, message="Greedy agent (no provider to test)")

    try:
        provider = create_provider(
            provider=agent.provider,
            model=agent.model,
            api_key_env=agent.api_key_env,
            base_url=agent.base_url,
            max_tokens=agent.max_tokens,
            supports_vision=agent.supports_vision,
            num_ctx=getattr(agent, "num_ctx", None),
        )
    except ProviderError as e:
        return AgentTestResult(success=False, message=str(e))

    ok, msg = provider.test_connection()
    return AgentTestResult(success=ok, message=msg)
