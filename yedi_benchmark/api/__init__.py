"""HTTP API layer for the Yedi benchmark web UI.

Each submodule is a FastAPI APIRouter. They are all mounted onto the main
FastAPI app in `gym_server.py` via `mount_api_routers(app)`.

Routers:
  - routes_agents:  /api/agents (CRUD + connection test)
  - routes_prompts: /api/prompts (CRUD + activate + clone)
  - routes_configs: /api/configs (read-only listing of game configs/tiers)
  - routes_runs:    /api/runs (start, list, get, cancel, delete)

Singletons:
  - The registries are exposed via dependency injectors in `deps.py` so tests
    can override them with isolated tmp dirs.
  - The run executor is a process-wide singleton that enforces a single
    active run at a time.
"""

from fastapi import FastAPI

from .routes_agents import router as agents_router
from .routes_bridge import router as bridge_router
from .routes_prompts import router as prompts_router
from .routes_configs import router as configs_router
from .routes_runs import router as runs_router


def mount_api_routers(app: FastAPI) -> None:
    """Attach all Phase 2 routers to the given FastAPI app."""
    app.include_router(agents_router)
    app.include_router(prompts_router)
    app.include_router(configs_router)
    app.include_router(runs_router)
    app.include_router(bridge_router)


__all__ = ["mount_api_routers"]
