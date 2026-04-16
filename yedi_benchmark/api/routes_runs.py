"""/api/runs — start, list, get, cancel, delete benchmark runs.

The actual benchmark execution happens in the RunExecutor singleton (one
worker thread, single-run lock). The routes are thin: validate, hand off,
read back from the run registry.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..bridge_status import BridgeStatus
from ..providers.registry import smoke_test_agent
from ..registries import AgentRegistry, RunRecord, RunRegistry, RunStatus
from ..registries.agents import AgentRegistryError
from ..registries.runs import RunRegistryError
from ..run_trace import get_run_trace_store
from .deps import get_agent_registry, get_bridge_status, get_run_registry
from .run_executor import ExecutorBusyError, RunExecutor, get_run_executor
from .schemas import RunActiveStatus, RunCreate

logger = logging.getLogger("api.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunRecord])
def list_runs(
    status: Optional[RunStatus] = Query(default=None),
    reg: RunRegistry = Depends(get_run_registry),
) -> list[RunRecord]:
    return reg.list(status=status)


@router.get("/active", response_model=RunActiveStatus)
def get_active_run(
    executor: RunExecutor = Depends(get_run_executor),
    reg: RunRegistry = Depends(get_run_registry),
) -> RunActiveStatus:
    """Lightweight current-run snapshot for the UI poll loop."""
    run_id = executor.get_active_run_id()
    if run_id is None:
        return RunActiveStatus(active=False)

    try:
        record = reg.get(run_id)
    except RunRegistryError:
        return RunActiveStatus(active=False)

    return RunActiveStatus(
        active=True,
        run_id=record.id,
        status=record.status.value,
        episodes_done=record.episodes_done(),
        episodes_total=record.episodes_total(),
    )


@router.get("/{run_id}", response_model=RunRecord)
def get_run(
    run_id: str,
    reg: RunRegistry = Depends(get_run_registry),
) -> RunRecord:
    try:
        return reg.get(run_id)
    except RunRegistryError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=RunRecord, status_code=201)
def create_run(
    body: RunCreate,
    reg: RunRegistry = Depends(get_run_registry),
    agents: AgentRegistry = Depends(get_agent_registry),
    executor: RunExecutor = Depends(get_run_executor),
    bridge: BridgeStatus = Depends(get_bridge_status),
) -> RunRecord:
    """Kick off a benchmark run.

    Returns 409 if a run is already in progress (single-run lock).
    Returns 400 if no browser tab is currently connected to ``/ws/game`` —
    otherwise the agent would talk to a dead bridge and every episode would
    silently complete with garbage observations.
    Returns 400 if the agent's pre-run smoke test fails (bad key, local
    server down, model not pulled, etc). This fails fast at POST time
    instead of letting the worker thread spawn and crash on the first LLM
    call.
    """
    # When workers > 1, the parallel runner spawns its own server+browser
    # pairs, so the main server's bridge state is irrelevant.
    if body.workers <= 1 and not bridge.is_game_connected():
        raise HTTPException(
            400,
            "No browser game is connected to /ws/game. Open the Game tab "
            "(in agent mode) and wait for it to load before launching a run.",
        )

    # Vision modes cannot be combined with merge_previews. The previews block
    # is pre-computed from real card values, so it trivialises the visual
    # perception test AND leaks every memory-hidden card's value via its
    # per-dimension gain tiers. The UI disables the checkbox on vision modes,
    # this rejects the same combination for API/CLI callers.
    if body.mode.value.startswith("vision") and body.show_merge_previews:
        raise HTTPException(
            400,
            "show_merge_previews is not compatible with vision modes. "
            "The merge_previews block contains pre-computed per-dimension "
            "gains that bypass visual perception and leak memory-hidden "
            "card values. Disable it to run a vision benchmark.",
        )

    # Vision modes require GPU-rendered screenshots. Parallel workers use
    # Xvfb + SwiftShader (software rendering) which produces visually
    # different output that would compromise VLM evaluation. Force single
    # worker for vision benchmarks.
    if body.mode.value.startswith("vision") and body.workers > 1:
        raise HTTPException(
            400,
            "Vision modes require a single worker. Parallel workers use "
            "software rendering (SwiftShader) which produces different "
            "visuals than GPU rendering, compromising VLM evaluation.",
        )

    # Pre-run smoke test: look up the agent here (rather than letting the
    # worker thread do it) so we can probe its provider and reject the POST
    # with a readable error BEFORE any run record is created. Random and
    # greedy baselines short-circuit to success inside smoke_test_agent.
    try:
        agent_cfg = agents.get(body.agent_id)
    except AgentRegistryError as e:
        raise HTTPException(400, str(e))

    ok, msg = smoke_test_agent(agent_cfg)
    if not ok:
        raise HTTPException(
            400,
            f"Agent smoke test failed for {agent_cfg.name!r}: {msg}. "
            f"Check that the provider is reachable and the model is available.",
        )

    try:
        record = executor.start(
            run_registry=reg,
            agent_id=body.agent_id,
            prompt_id=body.prompt_id,
            mode=body.mode.value,
            configs=list(body.configs),
            episodes_per_config=body.episodes_per_config,
            max_steps=body.max_steps,
            server_url=body.server_url,
            log_dir=body.log_dir,
            show_merge_previews=body.show_merge_previews,
            perfect_memory=body.perfect_memory,
            workers=body.workers,
        )
        return record
    except ExecutorBusyError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        # Validation failures from the registries (unknown agent, no active
        # prompt, etc.) bubble up here. We surface them as 400 so the UI
        # shows a useful error.
        logger.exception("create_run failed")
        raise HTTPException(400, str(e))


@router.post("/{run_id}/cancel")
def cancel_run(
    run_id: str,
    executor: RunExecutor = Depends(get_run_executor),
) -> dict:
    """Request cancellation of an in-flight run.

    Cancellation is cooperative: the worker checks the cancel flag between
    episodes, so this returns immediately and the run transitions to
    CANCELLED shortly after.
    """
    requested = executor.cancel(run_id)
    if not requested:
        raise HTTPException(404, "no matching run is currently running")
    return {"cancelled": True, "run_id": run_id}


@router.delete("/{run_id}", status_code=204, response_class=Response)
def delete_run(
    run_id: str,
    reg: RunRegistry = Depends(get_run_registry),
    executor: RunExecutor = Depends(get_run_executor),
) -> Response:
    if executor.get_active_run_id() == run_id:
        raise HTTPException(409, "cannot delete a run that is currently running")
    try:
        reg.delete(run_id)
    except RunRegistryError as e:
        raise HTTPException(404, str(e))
    get_run_trace_store().drop(run_id)
    return Response(status_code=204)


@router.get("/{run_id}/trace")
def get_run_trace(run_id: str, since: int = Query(default=0, ge=0)) -> dict:
    """Live trace of LLM exchanges for a run.

    Cursor-based polling: pass ``?since=N`` (the previous response's
    ``cursor``) to get only new entries. Returns an empty entries list if
    the run has no trace yet (e.g. random agent, or run not started).
    """
    trace = get_run_trace_store().get(run_id)
    if trace is None:
        return {
            "run_id": run_id,
            "cursor": 0,
            "system_prompts": {},
            "entries": [],
            "available": False,
        }
    snap = trace.snapshot(since_id=since)
    snap["available"] = True
    return snap
