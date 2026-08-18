# SPDX-License-Identifier: MIT
"""P11 Skill-Wizard: gefuehrte Neuanlage eines Skills ueber catalog.py.

Schliesst Ampel-Zeile 6 ("Skillgenerator mit Wizard") -- siehe
adapters/skills_catalog.py fuer die Herleitung und die bewusste Grenze:

WAS DIESER WIZARD TUT: Geruest anlegen (catalog.py create), das
`description:`-Pflichtfeld ausfuellen (das die CLI bisher als
"{{Beschreibung der Faehigkeit}}"-Platzhalter stehen laesst) und S-Tests
laufen lassen (Frontmatter/Struktur, `--type static`, kein LLM-Aufruf).

WAS ER NICHT TUT (bewusst, kein halbfertiger Nachbau): den eigentlichen
SKILL.md-KOERPER (die Anweisungen) schreiben, Testfaelle mit Subagenten
fahren, Beschreibung per LLM-Optimierungsschleife verbessern, committen/
pushen im skills-Repo. Das bleibt Aufgabe der konversationellen
`skill-creator`/`skill-extractor`-Skills -- der letzte Schritt des Wizards
nennt das ausdruecklich als naechsten Schritt, statt es stillschweigend
wegzulassen.

Die Beschreibungs-Felder ("was tut der Skill" + "wann triggert er") folgen
der Struktur von skill-creators eigenem "Capture Intent"-Abschnitt: dessen
Regel "All 'when to use' info goes here [description], not in the body"
ist der Grund, warum der Wizard beide Antworten zu EINEM description-Text
zusammenfuehrt, statt sie getrennt in Koerper und Frontmatter zu verteilen.

Rollen-Gating wie P5/P2: Schreibpfade (create/describe/validate) verlangen
Rolle admin, WENN eine Host-Session mit Rolle vorliegt; ohne Host-Auth
(Standalone/BACH-Mount) bleibt das Verhalten wie zuvor -- kein neuer Zwang,
wo bisher keiner war (ADAPTER-CONTRACT.md Sec. 5).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.skills_catalog import SkillsCatalogAdapter
from ..capabilities import Capability
from .base import PanelSpec

if TYPE_CHECKING:  # pragma: no cover
    from ..adapters.host_auth import HostAuthAdapter

# Mined aus der skill-creator-SKILL.md (Capture-Intent + Anatomy + Principle of
# Lack of Surprise) -- Hinweistexte, nicht Behauptungen ueber Funktionsumfang.
# Wird als Daten (nicht hartcodiertes HTML) ausgeliefert, damit die Herkunft
# an einer Stelle pflegbar bleibt.
GUIDANCE = {
    "what": "Was soll dieser Skill Claude ermoeglichen zu tun?",
    "when": "Wann soll er triggern -- welche Nutzerformulierungen/Kontexte? "
            "Sei ruhig etwas 'pushy': lieber zu viele Trigger-Situationen nennen "
            "als zu wenige -- Skills werden eher zu selten als zu oft ausgeloest.",
    "anatomy": "Ein Skill ist ein Ordner mit SKILL.md (Pflicht: name + description) "
               "plus optional scripts/ (ausfuehrbarer Code), references/ (Dokus bei Bedarf "
               "geladen) und assets/ (Vorlagen/Dateien fuer die Ausgabe).",
    "lack_of_surprise": "Ein Skill darf niemanden ueberraschen: sein Inhalt muss zu dem "
                        "passen, was sein Name und seine Beschreibung versprechen.",
    "next_steps": "Dieser Wizard legt Geruest + Beschreibung an und prueft die Struktur. "
                  "Die eigentlichen Anweisungen (der SKILL.md-Koerper) schreibt am besten "
                  "die konversationelle skill-creator-Skill mit dir zusammen -- inkl. "
                  "Testfaellen und Beschreibungs-Optimierung.",
}


class CreateRequest(BaseModel):
    name: str
    category: str
    type: str = "skill"


class DescribeRequest(BaseModel):
    name: str
    category: str
    what: str
    when: str


class ValidateRequest(BaseModel):
    name: str


def build(adapter: SkillsCatalogAdapter, auth_adapter: "HostAuthAdapter | None" = None) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    def _require_admin_for_write(request: Request) -> None:
        if auth_adapter is None:
            return
        user = auth_adapter.current_user(request)
        if user is None:
            return
        if user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Nur die Rolle 'admin' darf ueber den Skill-Wizard schreiben.")

    @router.get("/api/p11/guidance")
    def guidance():
        return GUIDANCE

    @router.get("/api/p11/categories")
    def categories():
        return _guard(adapter.categories)

    @router.post("/api/p11/create")
    def create(req: CreateRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.create(req.name, req.category, req.type))

    @router.post("/api/p11/describe")
    def describe(req: DescribeRequest, request: Request):
        _require_admin_for_write(request)
        what = req.what.strip()
        when = req.when.strip()
        if not what or not when:
            raise HTTPException(status_code=400, detail="Beide Felder (was/wann) sind Pflicht.")
        description = f"{what} {when}".strip()
        return _guard(lambda: adapter.set_description(req.name, req.category, description))

    @router.post("/api/p11/validate")
    def validate(req: ValidateRequest, request: Request):
        _require_admin_for_write(request)
        return _guard(lambda: adapter.quality(req.name))

    return PanelSpec(
        id="p11",
        label="Skill-Wizard",
        path="/p11",
        template="p11_skill_wizard.html",
        required={Capability.SKILLS_CREATE},
        router=router,
    )
