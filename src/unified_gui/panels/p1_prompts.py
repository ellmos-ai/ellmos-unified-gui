# SPDX-License-Identifier: MIT
"""P1 Prompts: BACH-Prompt-Bibliothek (versioniert) + profiprompt-v1-Export
+ PromptBoard-Import. Proxy auf BACHs /api/prompt-library (v3.13.0-bluesky)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..capabilities import Capability
from .base import PanelSpec


class PromptCreateRequest(BaseModel):
    name: str
    text: str
    category: str | None = None
    tags: str | None = None
    purpose: str | None = None


class PromptUpdateRequest(BaseModel):
    id: int
    text: str
    tags: str | None = None


def build(adapter: BachAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p1/prompts")
    def list_prompts(q: str | None = None, category: str | None = None):
        return _guard(lambda: adapter.prompts(q=q, category=category))

    @router.get("/api/p1/prompts/{prompt_id}")
    def get_prompt(prompt_id: int):
        return _guard(lambda: adapter.prompt(prompt_id))

    @router.post("/api/p1/prompts")
    def create_prompt(req: PromptCreateRequest):
        return _guard(lambda: adapter.prompt_create(req.model_dump()))

    @router.post("/api/p1/prompts/update")
    def update_prompt(req: PromptUpdateRequest):
        return _guard(lambda: adapter.prompt_update(req.id, {"text": req.text, "tags": req.tags}))

    @router.post("/api/p1/prompts/{prompt_id}/delete")
    def delete_prompt(prompt_id: int):
        return _guard(lambda: adapter.prompt_delete(prompt_id))

    @router.post("/api/p1/import-promptboard")
    def import_promptboard():
        return _guard(adapter.prompt_import_promptboard)

    @router.get("/api/p1/export-v1")
    def export_v1():
        data = _guard(adapter.export_v1)
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": 'attachment; filename="profiprompt-library-v1.json"'},
        )

    return PanelSpec(
        id="p1",
        label="Prompts",
        path="/p1",
        template="p1_prompts.html",
        required={Capability.PROMPTS_RW},
        router=router,
    )
