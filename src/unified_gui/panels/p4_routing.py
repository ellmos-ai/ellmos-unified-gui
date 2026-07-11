# SPDX-License-Identifier: MIT
"""P4 Routing: ticket-master-Score/Tiers editieren + clutch-Routing live.

Zwei Routing-Welten nebeneinander (bewusst nicht verschmolzen):
- ticket-master: Score-Formel -> Tier -> Provider (Konfig-Editor, Wahrheit =
  ticket-master.config.json)
- clutch: auto-lernender Router (Statistik + Route-Vorschau, read-only)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.clutch import ClutchAdapter
from ..adapters.ticket_master import TicketMasterAdapter
from ..capabilities import Capability, CapabilityRegistry
from .base import PanelSpec


class RoutingConfigRequest(BaseModel):
    score_thresholds: dict | None = None
    default_provider: str | None = None
    router_command: str | None = None
    advisor: dict | None = None


class RoutePreviewRequest(BaseModel):
    task: str


def build(ticket_master: TicketMasterAdapter, clutch: ClutchAdapter,
          registry: CapabilityRegistry) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _clutch_available() -> bool:
        state = next((s for s in registry.states if s.adapter is clutch), None)
        return state is not None and Capability.ROUTING_STATS in state.capabilities

    @router.get("/api/p4/config")
    def get_config():
        return {
            "ticket_master": _guard(ticket_master.routing_config),
            "clutch_available": _clutch_available(),
        }

    @router.post("/api/p4/config")
    def set_config(req: RoutingConfigRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="Keine Aenderungen uebergeben")
        return _guard(lambda: ticket_master.set_routing_config(updates))

    @router.get("/api/p4/clutch-stats")
    def clutch_stats():
        return _guard(clutch.stats)

    @router.post("/api/p4/clutch-route")
    def clutch_route(req: RoutePreviewRequest):
        if not req.task.strip():
            raise HTTPException(status_code=400, detail="Task-Text fehlt")
        return _guard(lambda: clutch.route_preview(req.task.strip()))

    return PanelSpec(
        id="p4",
        label="Routing",
        path="/p4",
        template="p4_routing.html",
        required={Capability.ROUTING_CONFIG},
        router=router,
    )
