# SPDX-License-Identifier: MIT
"""P8 Tickets: Intake, Score-/Routing-Vorschau, Queue-Board (ticket-master)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.ticket_master import TicketMasterAdapter
from ..capabilities import Capability
from .base import PanelSpec


class IntakeRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    urgency: str = "woche"
    project: str = "n/a"
    pipeline: str = "n/a"


class ScoreRequest(BaseModel):
    clarity: int = 5
    complexity: int = 5
    creativity: int = 0
    context: int = 5
    criticality: int = 0


class MoveRequest(BaseModel):
    id: str
    queue: str


def build(adapter: TicketMasterAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p8/queues")
    def queues():
        return _guard(adapter.queues)

    @router.post("/api/p8/intake")
    def intake(req: IntakeRequest):
        return _guard(lambda: adapter.intake(
            title=req.title, description=req.description, priority=req.priority,
            urgency=req.urgency, project=req.project, pipeline=req.pipeline,
        ))

    @router.post("/api/p8/score")
    def score(req: ScoreRequest):
        suggestion = _guard(lambda: adapter.score_preview(
            req.clarity, req.complexity, req.creativity, req.context, req.criticality,
        ))
        return suggestion.as_dict()

    @router.post("/api/p8/move")
    def move(req: MoveRequest):
        return _guard(lambda: adapter.move(req.id, req.queue))

    return PanelSpec(
        id="p8",
        label="Tickets",
        path="/p8",
        template="p8_tickets.html",
        required={Capability.TICKETS_RW},
        router=router,
    )
