# SPDX-License-Identifier: MIT
"""P2 Agenten: BACH-Agenten steuern (Start/Stop/Steer/Checkpoint) via CLI-JSON.

Hinweis: CLI-Aufrufe dauern wegen BACH-Startup-Hooks mehrere Sekunden — das
Frontend zeigt einen Laufindikator; hier gibt es kein Caching (Wahrheit = BACH).

Rollen-Gating (optional, additiv, 2026-08-18 — zweites Panel nach P5, gleiches
Muster: siehe adapters/host_auth.py + p5_permissions.py fuer die volle
Begruendung). Agenten starten/stoppen/steuern ist die staerkere Aktion als
eine Permission-Regel aendern (laufende Compute-Kosten, moegliche Stoerung
fremder Sitzungen) — deshalb hier ebenfalls "nur admin", wenn eine
Host-Session mit Rolle vorliegt. `list_agents` (Lesen) bleibt offen. Ohne
Host-Auth (Standalone, BACH-Mount, oder ellmos-core ohne aktive Session)
unveraendert wie zuvor."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..capabilities import Capability
from .base import PanelSpec

if TYPE_CHECKING:  # pragma: no cover
    from ..adapters.host_auth import HostAuthAdapter


class AgentActionRequest(BaseModel):
    name: str
    model: str | None = None
    mode: str | None = None
    note: str | None = None


def build(adapter: BachAdapter, auth_adapter: "HostAuthAdapter | None" = None) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _require_admin_for_write(request: Request) -> None:
        """Identisches Muster zu p5_permissions._require_admin_for_write:
        wirkt nur, wenn eine Host-Session mit Rolle tatsaechlich vorliegt."""
        if auth_adapter is None:
            return
        user = auth_adapter.current_user(request)
        if user is None:
            return
        if user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Nur die Rolle 'admin' darf Agenten starten, stoppen oder steuern.")

    @router.get("/api/p2/agents")
    def list_agents():
        return _guard(adapter.agents)

    @router.post("/api/p2/start")
    def start(req: AgentActionRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.agent_start(req.name, model=req.model, mode=req.mode))

    @router.post("/api/p2/stop")
    def stop(req: AgentActionRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.agent_stop(req.name))

    @router.post("/api/p2/steer")
    def steer(req: AgentActionRequest, request: Request):
        _require_admin_for_write(request)
        if not (req.note or "").strip():
            raise HTTPException(status_code=400, detail="Steer-Hinweis fehlt")
        return _guard(lambda: adapter.agent_steer(req.name, req.note.strip()))

    @router.post("/api/p2/clear-steer")
    def clear_steer(req: AgentActionRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.agent_clear_steer(req.name))

    @router.post("/api/p2/checkpoint")
    def checkpoint(req: AgentActionRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.agent_checkpoint(req.name))

    return PanelSpec(
        id="p2",
        label="Agenten",
        path="/p2",
        template="p2_agents.html",
        required={Capability.AGENT_DISPATCH},
        router=router,
    )
