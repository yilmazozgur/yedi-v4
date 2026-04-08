"""Agent registry — JSON-backed CRUD for AgentConfig records.

Storage: <data_dir>/agents.json
Format: {"agents": [<AgentConfig>, ...]}

The registry seeds itself on first load with a starter set of agents
(random + Claude/OpenAI/Gemini defaults).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import AgentConfig
from .paths import get_data_dir


_DEFAULT_FILENAME = "agents.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_default_seed() -> list[AgentConfig]:
    """Return the starter set of agents created on first launch.

    The "random" and "greedy" baselines are always present (no API key
    required). Three LLM agents are seeded as examples; the user can
    edit/delete them in the UI.
    """
    return [
        AgentConfig(
            name="Random",
            provider="random",
            model="",
            api_key_env=None,
            supports_vision=False,
        ),
        AgentConfig(
            name="Greedy",
            provider="greedy",
            model="",
            api_key_env=None,
            supports_vision=False,
        ),
        AgentConfig(
            name="Claude Sonnet 4.5",
            provider="anthropic",
            model="claude-sonnet-4-5",
            api_key_env="ANTHROPIC_API_KEY",
            max_tokens=512,
            supports_vision=True,
        ),
        AgentConfig(
            name="GPT-4o",
            provider="openai",
            model="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            max_tokens=512,
            supports_vision=True,
        ),
        AgentConfig(
            name="Gemini 2.5 Pro",
            provider="google",
            model="gemini/gemini-2.5-pro",
            api_key_env="GEMINI_API_KEY",
            max_tokens=512,
            supports_vision=True,
        ),
    ]


class AgentRegistryError(Exception):
    """Raised on registry constraint violations."""


class AgentRegistry:
    """Thread-safe JSON-backed agent registry.

    Usage:
        reg = AgentRegistry()       # uses default data dir
        reg.list()                   # -> list[AgentConfig]
        reg.get(agent_id)            # -> AgentConfig
        reg.create(agent_config)     # -> AgentConfig
        reg.update(id, **fields)     # -> AgentConfig
        reg.delete(id)               # -> None
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = Path(data_dir) if data_dir else get_data_dir()
        self._path = self._data_dir / _DEFAULT_FILENAME
        self._lock = threading.RLock()
        self._ensure_seeded()

    # ----- internal -----

    def _ensure_seeded(self) -> None:
        with self._lock:
            if self._path.exists():
                return
            self._path.parent.mkdir(parents=True, exist_ok=True)
            seed = get_default_seed()
            self._write([a.model_dump() for a in seed])

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("agents", [])

    def _write(self, agents: list[dict]) -> None:
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump({"agents": agents}, f, indent=2)
        tmp.replace(self._path)

    # ----- public CRUD -----

    def list(self) -> list[AgentConfig]:
        with self._lock:
            return [AgentConfig.model_validate(a) for a in self._read()]

    def get(self, agent_id: str) -> AgentConfig:
        with self._lock:
            for a in self._read():
                if a["id"] == agent_id:
                    return AgentConfig.model_validate(a)
        raise AgentRegistryError(f"agent not found: {agent_id}")

    def get_by_name(self, name: str) -> Optional[AgentConfig]:
        with self._lock:
            for a in self._read():
                if a["name"] == name:
                    return AgentConfig.model_validate(a)
        return None

    def create(self, agent: AgentConfig) -> AgentConfig:
        with self._lock:
            agents = self._read()
            # Name uniqueness
            if any(a["name"] == agent.name for a in agents):
                raise AgentRegistryError(f"agent name already exists: {agent.name}")
            agents.append(agent.model_dump())
            self._write(agents)
            return agent

    def update(self, agent_id: str, **fields) -> AgentConfig:
        with self._lock:
            agents = self._read()
            idx = next((i for i, a in enumerate(agents) if a["id"] == agent_id), None)
            if idx is None:
                raise AgentRegistryError(f"agent not found: {agent_id}")
            current = AgentConfig.model_validate(agents[idx])
            # Forbid changing the id
            fields.pop("id", None)
            # Name uniqueness if name is being changed
            new_name = fields.get("name")
            if new_name and new_name != current.name:
                if any(a["name"] == new_name for a in agents if a["id"] != agent_id):
                    raise AgentRegistryError(f"agent name already exists: {new_name}")
            updated = current.model_copy(update={**fields, "updated_at": _now_iso()})
            agents[idx] = updated.model_dump()
            self._write(agents)
            return updated

    def delete(self, agent_id: str) -> None:
        with self._lock:
            agents = self._read()
            new = [a for a in agents if a["id"] != agent_id]
            if len(new) == len(agents):
                raise AgentRegistryError(f"agent not found: {agent_id}")
            self._write(new)
