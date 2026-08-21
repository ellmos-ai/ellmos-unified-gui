# SPDX-License-Identifier: MIT
"""App-Factory der Unified GUI.

create_app(): Standalone-App (mit Local-Guard).
mount(host_app, prefix): Einbettung als Sub-App in einen FastAPI-Host
(z. B. BACH gui/server.py oder ellmos-core) — Auth uebernimmt der Host.

Kein globaler Modul-Zustand: Registry/Panels/Config haengen an der App-Instanz.
Alle Panel-Router werden registriert; SICHTBAR (Nav + Seite) ist ein Panel nur,
wenn seine required_capabilities aktuell geprobt sind — ein spaeter gestartetes
Backend wird per Re-Probe sichtbar, ohne App-Neustart.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..adapters.bach import BachAdapter
from ..adapters.clutch import ClutchAdapter
from ..adapters.compare_race import CompareRaceAdapter
from ..adapters.controlcenter import ControlCenterAdapter
from ..adapters.decisions import DecisionsAdapter
from ..adapters.host_auth import HostAuthAdapter
from ..adapters.lock_master import LockMasterAdapter
from ..adapters.ollama import OllamaAdapter
from ..adapters.scanner_tasks import ScannerTasksAdapter
from ..adapters.skills_catalog import SkillsCatalogAdapter
from ..adapters.ticket_master import TicketMasterAdapter
from ..audit_middleware import AuditMiddleware
from ..capabilities import CapabilityRegistry
from ..config import UnifiedGuiConfig
from ..panels import (p1_prompts, p2_agents, p3_models, p4_routing,
                      p5_permissions, p6_routines, p7_tasks, p8_tickets,
                      p9_skills, p10_decisions, p11_skill_wizard, p12_races)
from ..panels.base import PanelSpec
from ..security import LocalOnlyMiddleware

_WEB_DIR = Path(__file__).parent


def create_app(config: UnifiedGuiConfig | dict | None = None, *,
               standalone_guard: bool | None = None) -> FastAPI:
    if isinstance(config, dict):
        config = UnifiedGuiConfig.load(overrides=config)
    elif config is None:
        config = UnifiedGuiConfig.load()

    from .. import __version__  # lokal, vermeidet Import-Zyklus beim Paket-Init

    app = FastAPI(title=config.title, version=__version__, docs_url=None, redoc_url=None)

    registry = CapabilityRegistry()
    lock_adapter = LockMasterAdapter(config.lock_master)
    ticket_adapter = TicketMasterAdapter(config.ticket_master)
    bach_adapter = BachAdapter(config.bach)
    scanner_adapter = ScannerTasksAdapter(config.scanner_tasks)
    clutch_adapter = ClutchAdapter(config.clutch)
    ollama_adapter = OllamaAdapter(config.ollama)
    controlcenter_adapter = ControlCenterAdapter(config.controlcenter)
    decisions_adapter = DecisionsAdapter(config.decisions)
    skills_catalog_adapter = SkillsCatalogAdapter(config.skills_catalog)
    compare_race_adapter = CompareRaceAdapter(config.compare_race)
    # Nur wirksam im ellmos-core-Mount-Betrieb (siehe adapters/host_auth.py);
    # ueberall sonst probt sie leer und aendert nichts am bisherigen Verhalten.
    host_auth_adapter = HostAuthAdapter()
    for adapter in (lock_adapter, ticket_adapter, bach_adapter, scanner_adapter,
                    clutch_adapter, ollama_adapter, controlcenter_adapter,
                    decisions_adapter, skills_catalog_adapter, compare_race_adapter,
                    host_auth_adapter):
        registry.register(adapter)

    all_panels: list[PanelSpec] = [
        p1_prompts.build(bach_adapter),
        p2_agents.build(bach_adapter, host_auth_adapter),
        p3_models.build(clutch_adapter, ollama_adapter, registry),
        p4_routing.build(ticket_adapter, clutch_adapter, registry),
        p5_permissions.build(lock_adapter, host_auth_adapter),
        p6_routines.build(bach_adapter),
        p7_tasks.build(bach_adapter, scanner_adapter, registry),
        p8_tickets.build(ticket_adapter),
        p9_skills.build(controlcenter_adapter),
        # lock_adapter mit: P10 schreibt und prueft dafuer LOCK.permissions.json
        p10_decisions.build(decisions_adapter, lock_adapter),
        p11_skill_wizard.build(skills_catalog_adapter, host_auth_adapter),
        p12_races.build(compare_race_adapter),
    ]

    app.state.config = config
    app.state.registry = registry
    app.state.all_panels = all_panels

    def visible_panels() -> list[PanelSpec]:
        return [p for p in all_panels if registry.supports(p.required)]

    guard = config.local_only if standalone_guard is None else standalone_guard
    if guard:
        app.add_middleware(LocalOnlyMiddleware)
    # Audit-Log fuer zustandsaendernde Aktionen -- wirkt automatisch auch im
    # Mount-Betrieb, da mount() diese Funktion aufruft (siehe deren Docstring).
    app.add_middleware(AuditMiddleware, auth_adapter=host_auth_adapter,
                       audit_log_path=config.audit_log_path)

    templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")

    def _ctx(request: Request, extra: dict | None = None) -> dict:
        base = {
            "request": request,
            "title": config.title,
            "version": __version__,
            "panels": visible_panels(),
            # root_path macht Links mount-sicher (Host mountet unter /prefix)
            "base": request.scope.get("root_path", ""),
        }
        if extra:
            base.update(extra)
        return base

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        states = [
            {
                "name": s.adapter.name,
                "label": s.adapter.label,
                "capabilities": sorted(c.value for c in s.capabilities),
                "health": s.adapter.health().__dict__,
                "probe_error": s.probe_error,
            }
            for s in registry.states
        ]
        return templates.TemplateResponse(request, "index.html", _ctx(request, {"adapters": states}))

    # Bewusst sync (def): Adapter-Probes machen blockierende HTTP-Calls — im
    # Mount-Betrieb u. U. auf den EIGENEN Host (BACH :8000). Sync-Handler laufen
    # im Threadpool, der Event-Loop bleibt frei -> kein Self-Call-Deadlock.
    @app.post("/api/refresh")
    def refresh():
        registry.refresh()
        return {
            "ok": True,
            "available": sorted(c.value for c in registry.available),
            "panels": [p.id for p in visible_panels()],
        }

    @app.get("/api/status")
    def status():
        return {
            "version": __version__,
            "available": sorted(c.value for c in registry.available),
            "panels": [p.id for p in visible_panels()],
        }

    def _make_page(panel: PanelSpec):
        async def page(request: Request):
            if not registry.supports(panel.required):
                # Backend (noch) nicht da -> zurueck zur Uebersicht statt Fehlerseite
                return RedirectResponse(url=request.scope.get("root_path", "") + "/", status_code=302)
            return templates.TemplateResponse(request, panel.template, _ctx(request, {"panel": panel}))
        return page

    for panel in all_panels:
        if panel.router is not None:
            app.include_router(panel.router)
        app.add_api_route(panel.path, _make_page(panel), methods=["GET"],
                          response_class=HTMLResponse, include_in_schema=False)

    return app


def mount(host_app: FastAPI, prefix: str = "/control",
          config: UnifiedGuiConfig | dict | None = None) -> FastAPI:
    """Unified GUI als Sub-App in einen Host einhaengen. Gibt die Sub-App zurueck."""
    sub_app = create_app(config, standalone_guard=False)
    host_app.mount(prefix, sub_app)
    return sub_app
