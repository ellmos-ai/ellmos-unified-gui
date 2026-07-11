# SPDX-License-Identifier: MIT
"""P9 Skills: Inventar + Intent-Matching via ellmos-controlcenter-mcp.

Jeder Aufruf spawnt eine kurzlebige MCP-Session (Node) — dauert 1-3 s;
das Frontend zeigt einen Laufindikator.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.controlcenter import ControlCenterAdapter
from ..capabilities import Capability
from .base import PanelSpec


class IntentRequest(BaseModel):
    intent: str


def build(adapter: ControlCenterAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p9/skills")
    def skills():
        return _guard(adapter.skills)

    @router.post("/api/p9/find")
    def find(req: IntentRequest):
        if not req.intent.strip():
            raise HTTPException(status_code=400, detail="Intent fehlt")
        return _guard(lambda: adapter.find_skill(req.intent.strip()))

    @router.get("/api/p9/bundles")
    def bundles():
        return _guard(adapter.bundles)

    return PanelSpec(
        id="p9",
        label="Skills",
        path="/p9",
        template="p9_skills.html",
        required={Capability.SKILLS_DISCOVERY},
        router=router,
    )
