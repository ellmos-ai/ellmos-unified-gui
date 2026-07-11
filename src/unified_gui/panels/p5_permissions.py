# SPDX-License-Identifier: MIT
"""P5 Berechtigungen: Editor fuer LOCK.permissions.json + Lock-Uebersicht.

Sichtbar ab PERMISSIONS_RW; der Locks-Abschnitt degradiert, wenn LOCKS_RW
(Watcher) fehlt — Banner statt Fehler (ADAPTER-CONTRACT §5).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.lock_master import LockMasterAdapter
from ..capabilities import Capability
from .base import PanelSpec


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


def build(adapter: LockMasterAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

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
    def add_rule(req: RuleRequest):
        return _guard(lambda: adapter.add_rule(req.root, req.decision, req.pattern, req.agents))

    @router.post("/api/p5/rules/remove")
    def remove_rule(req: RuleRequest):
        return _guard(lambda: adapter.remove_rule(req.root, req.decision, req.pattern))

    @router.post("/api/p5/default")
    def set_default(req: DefaultRequest):
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
    def bulk_lock():
        return _guard(adapter.bulk_lock)

    @router.post("/api/p5/locks/bulk-unlock")
    def bulk_unlock():
        return _guard(adapter.bulk_unlock)

    return PanelSpec(
        id="p5",
        label="Berechtigungen",
        path="/p5",
        template="p5_permissions.html",
        required={Capability.PERMISSIONS_RW},
        router=router,
    )
