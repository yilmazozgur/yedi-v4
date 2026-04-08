"""/api/prompts — CRUD for PromptRegistry plus activate + clone."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response

from ..registries import Prompt, PromptRegistry
from ..registries.prompts import PromptRegistryError
from .deps import get_prompt_registry
from .schemas import PromptCloneRequest, PromptCreate, PromptUpdate

logger = logging.getLogger("api.prompts")

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=list[Prompt])
def list_prompts(reg: PromptRegistry = Depends(get_prompt_registry)) -> list[Prompt]:
    return reg.list()


@router.get("/active", response_model=Prompt)
def get_active_prompt(reg: PromptRegistry = Depends(get_prompt_registry)) -> Prompt:
    try:
        return reg.get_active()
    except PromptRegistryError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=Prompt, status_code=201)
def create_prompt(
    body: PromptCreate,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Prompt:
    try:
        new = Prompt(**body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    try:
        return reg.create(new)
    except PromptRegistryError as e:
        raise HTTPException(409, str(e))


@router.get("/{prompt_id}", response_model=Prompt)
def get_prompt(
    prompt_id: str,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Prompt:
    try:
        return reg.get(prompt_id)
    except PromptRegistryError as e:
        raise HTTPException(404, str(e))


@router.put("/{prompt_id}", response_model=Prompt)
def update_prompt(
    prompt_id: str,
    body: PromptUpdate,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Prompt:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        return reg.update(prompt_id, **fields)
    except PromptRegistryError as e:
        msg = str(e)
        status = 404 if "not found" in msg else 409
        raise HTTPException(status, msg)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{prompt_id}", status_code=204, response_class=Response)
def delete_prompt(
    prompt_id: str,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Response:
    try:
        reg.delete(prompt_id)
    except PromptRegistryError as e:
        msg = str(e)
        status = 404 if "not found" in msg else 409
        raise HTTPException(status, msg)
    return Response(status_code=204)


@router.post("/{prompt_id}/activate", response_model=Prompt)
def activate_prompt(
    prompt_id: str,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Prompt:
    try:
        return reg.activate(prompt_id)
    except PromptRegistryError as e:
        raise HTTPException(404, str(e))


@router.post("/{prompt_id}/clone", response_model=Prompt, status_code=201)
def clone_prompt(
    prompt_id: str,
    body: PromptCloneRequest,
    reg: PromptRegistry = Depends(get_prompt_registry),
) -> Prompt:
    try:
        return reg.clone(prompt_id, body.new_name)
    except PromptRegistryError as e:
        msg = str(e)
        status = 404 if "not found" in msg else 409
        raise HTTPException(status, msg)
