# SPDX-License-Identifier: MIT
"""P5 Berechtigungen: Editor fuer LOCK.permissions.json + Lock-Uebersicht.

Sichtbar ab PERMISSIONS_RW; der Locks-Abschnitt degradiert, wenn LOCKS_RW
(Watcher) fehlt — Banner statt Fehler (ADAPTER-CONTRACT §5).

Rollen-Gating (optional, additiv, 2026-08-18 — schliesst den TODO.md-Punkt
"Auth-Seam-Design im Mount-Betrieb"): Wenn ein `HostAuthAdapter` uebergeben
wird UND dieser eine Host-Session mit Rolle liefert (nur im ellmos-core-
Mount-Betrieb der Fall — `mount()` selbst dokumentiert "Auth uebernimmt der
Host"), duerfen NUR Personen mit Rolle "admin" die Regeln aendern. Ohne
Host-Auth (Standalone, BACH-Mount, oder ellmos-core ohne aktive Session)
bleibt das Verhalten exakt wie zuvor — kein neuer Zwang, wo bisher keiner
war. `ellmos-core` selbst wird NIE importiert wenn `auth_adapter` fehlt;
lock-master bleibt weiterhin die alleinige Quelle der Wahrheit fuer die
Regeln selbst (kein zweites Rechtesystem, nur eine zusaetzliche Gating-
Bedingung vor dem Schreibpfad)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.lock_master import LockMasterAdapter
from ..capabilities import Capability
from .base import PanelSpec

if TYPE_CHECKING:  # pragma: no cover
    from ..adapters.host_auth import HostAuthAdapter


class RuleRequest(BaseModel):
    root: str
    decision: str  # allow | deny | ask
    pattern: str
    agents: list[str] | None = None


class DefaultRequest(BaseModel):
    root: str
    default: str


class EvaluateRequest(BaseModel):
    root: str
    agent: str = "claude"
    action: str


def build(adapter: LockMasterAdapter, auth_adapter: "HostAuthAdapter | None" = None) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _require_admin_for_write(request: Request) -> None:
        """Gating vor Schreibaktionen: nur wirksam, wenn eine Host-Session
        mit Rolle tatsaechlich vorliegt (siehe Modul-Docstring). `None` an
        jeder Stelle (kein Adapter, kein Backend, keine Session) bedeutet
        "kein Nutzerkontext" und laesst den Schreibpfad unveraendert offen."""
        if auth_adapter is None:
            return
        user = auth_adapter.current_user(request)
        if user is None:
            return
        if user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Nur die Rolle 'admin' darf LOCK.permissions.json aendern.")

    @router.get("/api/p5/roots")
    def get_roots():
        roots = []
        for path in adapter.roots():
            has_file = any((path / name).is_file()
                           for name in ("LOCK.permissions.json", "LOCK.permissions.txt"))
            roots.append({"path": str(path), "has_permissions": has_file})
        return {"roots": roots}

    @router.get("/api/p5/rules")
    def get_rules(root: str):
        return _guard(lambda: adapter.rules(root))

    @router.post("/api/p5/rules")
    def add_rule(req: RuleRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.add_rule(req.root, req.decision, req.pattern, req.agents))

    @router.post("/api/p5/rules/remove")
    def remove_rule(req: RuleRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.remove_rule(req.root, req.decision, req.pattern))

    @router.post("/api/p5/default")
    def set_default(req: DefaultRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.set_default(req.root, req.default))

    @router.post("/api/p5/evaluate")
    def evaluate(req: EvaluateRequest):
        verdict = _guard(lambda: adapter.evaluate(req.root, req.agent, req.action))
        return {"verdict": verdict, "agent": req.agent, "action": req.action}

    # --- Locks (Watcher; degradiert wenn offline) ---
    @router.get("/api/p5/locks")
    def get_locks():
        return _guard(adapter.locks)

    @router.post("/api/p5/locks/scan")
    def scan():
        return _guard(adapter.scan)

    @router.post("/api/p5/locks/prune")
    def prune():
        return _guard(adapter.prune)

    @router.post("/api/p5/locks/bulk-lock")
    def bulk_lock(request: Request):
        _require_admin_for_write(request)
        return _guard(adapter.bulk_lock)

    @router.post("/api/p5/locks/bulk-unlock")
    def bulk_unlock(request: Request):
        _require_admin_for_write(request)
        return _guard(adapter.bulk_unlock)

    return PanelSpec(
        id="p5",
        label="Berechtigungen",
        path="/p5",
        template="p5_permissions.html",
        required={Capability.PERMISSIONS_RW},
        router=router,
    )
