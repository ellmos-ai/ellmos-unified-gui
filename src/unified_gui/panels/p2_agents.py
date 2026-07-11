# SPDX-License-Identifier: MIT
"""P2 Agenten: BACH-Agenten steuern (Start/Stop/Steer/Checkpoint) via CLI-JSON.

Hinweis: CLI-Aufrufe dauern wegen BACH-Startup-Hooks mehrere Sekunden — das
Frontend zeigt einen Laufindikator; hier gibt es kein Caching (Wahrheit = BACH).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..capabilities import Capability
from .base import PanelSpec


class AgentActionRequest(BaseModel):
    name: str
    model: str | None = None
    mode: str | None = None
    note: str | None = None


def build(adapter: BachAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p2/agents")
    def list_agents():
        return _guard(adapter.agents)

    @router.post("/api/p2/start")
    def start(req: AgentActionRequest):
        return _guard(lambda: adapter.agent_start(req.name, model=req.model, mode=req.mode))

    @router.post("/api/p2/stop")
    def stop(req: AgentActionRequest):
        return _guard(lambda: adapter.agent_stop(req.name))

    @router.post("/api/p2/steer")
    def steer(req: AgentActionRequest):
        if not (req.note or "").strip():
            raise HTTPException(status_code=400, detail="Steer-Hinweis fehlt")
        return _guard(lambda: adapter.agent_steer(req.name, req.note.strip()))

    @router.post("/api/p2/clear-steer")
    def clear_steer(req: AgentActionRequest):
        return _guard(lambda: adapter.agent_clear_steer(req.name))

    @router.post("/api/p2/checkpoint")
    def checkpoint(req: AgentActionRequest):
        return _guard(lambda: adapter.agent_checkpoint(req.name))

    return PanelSpec(
        id="p2",
        label="Agenten",
        path="/p2",
        template="p2_agents.html",
        required={Capability.AGENT_DISPATCH},
        router=router,
    )
