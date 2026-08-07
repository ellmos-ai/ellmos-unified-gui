# SPDX-License-Identifier: MIT
"""P10 Decisions: Entscheidungen sichten, durchklicken, einstellen.

Zwei Ausbaustufen, capability-gesteuert [D03]:

* **DECISIONS_RO** — GET-Routen ueber den generierten Index. Genau der Stand
  vom 2026-08-01; ohne die decision-clicker-Kernlogik bleibt es dabei.
* **DECISIONS_RW** — zusaetzlich POST-Routen: entscheiden, einstellen,
  Desktop-Postfach uebernehmen. Geschrieben wird ausschliesslich ueber den
  Adapter, nie aus dem Panel heraus [D03]; die Wahrheit bleibt die
  TO-DECIDE-Kette [D04]. Siehe [D11].

Vor jedem Schreibvorgang laeuft die Rechtepruefung gegen
`LOCK.permissions.json` (harte Projektregel). `deny` blockt; `ask` verlangt
eine ausdrueckliche Bestaetigung aus der Oberflaeche.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ..adapters.base import AdapterError
from ..adapters.decisions import DecisionsAdapter
from ..adapters.lock_master import LockMasterAdapter
from ..capabilities import Capability
from .base import PanelSpec

AGENT = "unified-gui"


def build(adapter: DecisionsAdapter, lock: LockMasterAdapter | None = None) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _permit(action: str, confirmed: bool) -> None:
        """LOCK.permissions.json fragen, bevor irgendetwas geschrieben wird.

        Ist lock-master nicht da oder der Kettenordner kein verwalteter Root,
        faellt die Pruefung aus — dann greifen weiterhin die Schutzmechanismen
        der Kernlogik (fremde LOCK-Dateien, Sicherung, kein Ueberschreiben).
        """
        root = adapter.chain_dir()
        if lock is None or not root:
            return
        try:
            verdict = lock.evaluate(root, AGENT, action)
        except Exception:  # noqa: BLE001 -- Rechte-Backend weg: nicht haerter blocken
            return
        if verdict == "deny":
            raise HTTPException(
                status_code=403,
                detail=f"permissions.deny: {root} verbietet '{action}' fuer {AGENT}.")
        if verdict == "ask" and not confirmed:
            raise HTTPException(
                status_code=428,
                detail=f"permissions.ask: {root} verlangt Bestaetigung fuer '{action}'.")

    # -- Lesen ------------------------------------------------------------
    @router.get("/api/p10/summary")
    def summary():
        return _guard(adapter.summary)

    @router.get("/api/p10/entries")
    def entries(scope: str | None = None, status_class: str | None = None):
        rows = _guard(lambda: adapter.entries(scope=scope, status_class=status_class))
        return {"entries": rows, "count": len(rows)}

    @router.get("/api/p10/status")
    def status():
        """Live-Stand aus der Kette — nur mit Schreibpfad verfuegbar."""
        return _guard(adapter.status)

    @router.get("/api/p10/open")
    def open_entries():
        rows = _guard(adapter.open_entries)
        return {"entries": rows, "count": len(rows)}

    @router.get("/api/p10/detail/{key:path}")
    def detail(key: str):
        return _guard(lambda: adapter.detail(key))

    @router.get("/api/p10/register")
    def register(q: str = ""):
        rows = _guard(lambda: adapter.register(q))
        return {"entries": rows, "count": len(rows)}

    @router.get("/api/p10/intake")
    def intake():
        rows = _guard(adapter.intake_pending)
        return {"pending": rows, "count": len(rows)}

    # -- Schreiben --------------------------------------------------------
    @router.post("/api/p10/decide")
    def decide(payload: dict = Body(...)):
        key = str(payload.get("key") or "").strip()
        choice = str(payload.get("choice") or "").strip()
        if not key or not choice:
            raise HTTPException(status_code=422, detail="key und choice sind Pflicht.")
        _permit("write", bool(payload.get("confirmed")))
        return _guard(lambda: adapter.decide(key, choice, str(payload.get("note") or "")))

    @router.post("/api/p10/new")
    def create(payload: dict = Body(...)):
        title = str(payload.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=422, detail="title ist Pflicht.")
        optionen = payload.get("optionen") or []
        if isinstance(optionen, str):
            optionen = [z for z in optionen.splitlines() if z.strip()]
        _permit("write", bool(payload.get("confirmed")))
        return _guard(lambda: adapter.create(
            title,
            frage=str(payload.get("frage") or ""),
            optionen=[str(o) for o in optionen],
            empfehlung=str(payload.get("empfehlung") or ""),
            kontext=str(payload.get("kontext") or ""),
            quelle=str(payload.get("quelle") or ""),
            scope=str(payload.get("scope") or ""),
        ))

    @router.post("/api/p10/intake")
    def intake_apply(payload: dict = Body(default={})):
        _permit("write", bool((payload or {}).get("confirmed")))
        rows = _guard(adapter.intake_apply)
        return {"ok": True, "uebernommen": rows, "count": len(rows)}

    return PanelSpec(
        id="p10",
        label="Decisions",
        path="/p10",
        template="p10_decisions.html",
        required={Capability.DECISIONS_RO},
        router=router,
    )
