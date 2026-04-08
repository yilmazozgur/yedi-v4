"""Prompt registry — JSON-backed CRUD for Prompt records.

Storage: <data_dir>/prompts.json
Format: {"prompts": [<Prompt>, ...]}

Invariants:
  - At most one prompt has is_active=True at any time.
  - Deleting the active prompt is forbidden until another is activated.
  - On first launch, seeds with the default v1 prompt extracted from
    agents.llm_agent's hardcoded constants.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .default_prompt import get_default_prompt
from .models import Prompt


_DEFAULT_FILENAME = "prompts.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromptRegistryError(Exception):
    """Raised on registry constraint violations."""


class PromptRegistry:
    """Thread-safe JSON-backed prompt registry."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            from .paths import get_data_dir
            data_dir = get_data_dir()
        self._data_dir = Path(data_dir)
        self._path = self._data_dir / _DEFAULT_FILENAME
        self._lock = threading.RLock()
        self._ensure_seeded()

    # ----- internal -----

    def _ensure_seeded(self) -> None:
        with self._lock:
            if self._path.exists():
                return
            self._path.parent.mkdir(parents=True, exist_ok=True)
            seed_prompt = get_default_prompt()
            self._write([seed_prompt.model_dump()])

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("prompts", [])

    def _write(self, prompts: list[dict]) -> None:
        tmp = self._path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump({"prompts": prompts}, f, indent=2)
        tmp.replace(self._path)

    def _enforce_single_active(self, prompts: list[dict]) -> list[dict]:
        """Ensure at most one prompt has is_active=True. Returns the cleaned list."""
        active = [p for p in prompts if p.get("is_active")]
        if len(active) <= 1:
            return prompts
        # If multiple flagged active, keep the one most recently updated.
        active.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        keeper_id = active[0]["id"]
        for p in prompts:
            if p.get("is_active") and p["id"] != keeper_id:
                p["is_active"] = False
        return prompts

    # ----- public CRUD -----

    def list(self) -> list[Prompt]:
        with self._lock:
            return [Prompt.model_validate(p) for p in self._read()]

    def get(self, prompt_id: str) -> Prompt:
        with self._lock:
            for p in self._read():
                if p["id"] == prompt_id:
                    return Prompt.model_validate(p)
        raise PromptRegistryError(f"prompt not found: {prompt_id}")

    def get_active(self) -> Prompt:
        with self._lock:
            prompts = self._read()
            for p in prompts:
                if p.get("is_active"):
                    return Prompt.model_validate(p)
        raise PromptRegistryError("no active prompt set")

    def create(self, prompt: Prompt) -> Prompt:
        with self._lock:
            prompts = self._read()
            if any(p["name"] == prompt.name for p in prompts):
                raise PromptRegistryError(f"prompt name already exists: {prompt.name}")
            # New prompts are inactive unless explicitly activated.
            prompt_dict = prompt.model_dump()
            prompt_dict["is_active"] = False
            prompts.append(prompt_dict)
            self._write(prompts)
            return Prompt.model_validate(prompt_dict)

    def update(self, prompt_id: str, **fields) -> Prompt:
        with self._lock:
            prompts = self._read()
            idx = next((i for i, p in enumerate(prompts) if p["id"] == prompt_id), None)
            if idx is None:
                raise PromptRegistryError(f"prompt not found: {prompt_id}")
            current = Prompt.model_validate(prompts[idx])
            # Forbid changing id and is_active via update — use activate() instead
            fields.pop("id", None)
            fields.pop("is_active", None)
            new_name = fields.get("name")
            if new_name and new_name != current.name:
                if any(p["name"] == new_name for p in prompts if p["id"] != prompt_id):
                    raise PromptRegistryError(f"prompt name already exists: {new_name}")
            updated = current.model_copy(update={**fields, "updated_at": _now_iso()})
            prompts[idx] = updated.model_dump()
            self._write(prompts)
            return updated

    def activate(self, prompt_id: str) -> Prompt:
        """Mark this prompt as the single active prompt; deactivate all others."""
        with self._lock:
            prompts = self._read()
            target_idx = next((i for i, p in enumerate(prompts) if p["id"] == prompt_id), None)
            if target_idx is None:
                raise PromptRegistryError(f"prompt not found: {prompt_id}")
            for i, p in enumerate(prompts):
                p["is_active"] = (i == target_idx)
                if i == target_idx:
                    p["updated_at"] = _now_iso()
            self._write(prompts)
            return Prompt.model_validate(prompts[target_idx])

    def delete(self, prompt_id: str) -> None:
        with self._lock:
            prompts = self._read()
            target = next((p for p in prompts if p["id"] == prompt_id), None)
            if target is None:
                raise PromptRegistryError(f"prompt not found: {prompt_id}")
            if target.get("is_active"):
                raise PromptRegistryError(
                    "cannot delete the active prompt; activate another first"
                )
            new = [p for p in prompts if p["id"] != prompt_id]
            self._write(new)

    def clone(self, prompt_id: str, new_name: str) -> Prompt:
        """Create a copy of an existing prompt with a new name and bumped version."""
        with self._lock:
            source = self.get(prompt_id)
            clone = Prompt(
                name=new_name,
                version=source.version + 1,
                core_rules=source.core_rules,
                dimension_rules=dict(source.dimension_rules),
                is_active=False,
            )
            return self.create(clone)
