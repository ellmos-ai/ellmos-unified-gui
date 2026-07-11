# SPDX-License-Identifier: MIT
"""P7 Tasks: Aggregation mehrerer Task-Quellen mit Provenienz + Zuweisung.

Quellen werden NICHT vereinheitlicht (DECISIONS.md D05) — jede Task traegt ihr
provenance-Feld ("bach", "scanner"); Zuweisung/Erledigung geht an die Quelle.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..adapters.scanner_tasks import ScannerTasksAdapter
from ..capabilities import Capability, CapabilityRegistry
from .base import PanelSpec


class TaskActionRequest(BaseModel):
    provenance: str  # "bach" | "scanner"
    id: int
    target: str | None = None


def build(bach: BachAdapter, scanner: ScannerTasksAdapter,
          registry: CapabilityRegistry) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _source(provenance: str):
        if provenance == "bach":
            return bach
        if provenance == "scanner":
            return scanner
        raise HTTPException(status_code=400, detail=f"Unbekannte Quelle: {provenance}")

    @router.get("/api/p7/tasks")
    def list_tasks(status: str = "all"):
        sources: list[dict] = []
        tasks: list[dict] = []
        for adapter, caps_needed in ((bach, Capability.TASKS_RO), (scanner, Capability.TASKS_RO)):
            state = next((s for s in registry.states if s.adapter is adapter), None)
            available = state is not None and caps_needed in state.capabilities
            entry = {"name": adapter.name, "available": available, "error": None, "count": 0}
            if available:
                try:
                    if adapter is scanner:
                        rows = adapter.tasks(status=None if status == "all" else status)
                    else:
                        rows = adapter.tasks(status=status)
                    entry["count"] = len(rows)
                    tasks.extend(rows)
                except AdapterError as exc:
                    entry["error"] = f"{exc.kind}: {exc.hint}"
            sources.append(entry)
        return {"tasks": tasks, "sources": sources}

    @router.post("/api/p7/assign")
    def assign(req: TaskActionRequest):
        if not (req.target or "").strip():
            raise HTTPException(status_code=400, detail="Zuweisungsziel fehlt")
        return _guard(lambda: _source(req.provenance).task_assign(req.id, req.target.strip()))

    @router.post("/api/p7/done")
    def done(req: TaskActionRequest):
        return _guard(lambda: _source(req.provenance).task_done(req.id))

    return PanelSpec(
        id="p7",
        label="Tasks",
        path="/p7",
        template="p7_tasks.html",
        required={Capability.TASKS_RO},
        router=router,
    )
