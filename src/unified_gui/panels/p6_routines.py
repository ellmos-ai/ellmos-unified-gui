# SPDX-License-Identifier: MIT
"""P6 Routinen/Cron: BACH-Scheduler (Jobs + Chains) ueber die Daemon-REST-API.

BACH ist der einzige echte Scheduler im Oekosystem — dieses Panel ist bewusst
ein View/Editor darauf, kein eigener Scheduler (DECISIONS.md D04). Die
Routine-Bindings (Modell/Rolle/Skills) folgen, sobald der Schreibpfad in BACH
geklaert ist (TODO.md "Offen").
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..capabilities import Capability
from .base import PanelSpec


class JobCreateRequest(BaseModel):
    name: str
    description: str | None = None
    job_type: str = "interval"
    schedule: str  # z. B. "30" (Minuten) — BACH-Daemon-Konvention
    command: str
    script_path: str | None = None


class IdRequest(BaseModel):
    id: int


def build(adapter: BachAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p6/overview")
    def overview():
        return {
            "status": _guard(adapter.daemon_status),
            "jobs": _guard(adapter.jobs),
            "chains": _guard(adapter.chains),
        }

    @router.get("/api/p6/runs")
    def runs():
        return _guard(adapter.runs)

    @router.post("/api/p6/jobs")
    def create_job(req: JobCreateRequest):
        return _guard(lambda: adapter.create_job(req.model_dump()))

    @router.post("/api/p6/jobs/toggle")
    def toggle_job(req: IdRequest):
        return _guard(lambda: adapter.toggle_job(req.id))

    @router.post("/api/p6/jobs/run")
    def run_job(req: IdRequest):
        return _guard(lambda: adapter.run_job(req.id))

    @router.post("/api/p6/chains/toggle")
    def toggle_chain(req: IdRequest):
        return _guard(lambda: adapter.toggle_chain(req.id))

    @router.post("/api/p6/chains/run")
    def run_chain(req: IdRequest):
        return _guard(lambda: adapter.run_chain(req.id))

    return PanelSpec(
        id="p6",
        label="Routinen",
        path="/p6",
        template="p6_routines.html",
        required={Capability.SCHEDULER_RW},
        router=router,
    )
