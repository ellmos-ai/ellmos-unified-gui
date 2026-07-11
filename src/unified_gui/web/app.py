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

from ..adapters.lock_master import LockMasterAdapter
from ..adapters.ticket_master import TicketMasterAdapter
from ..capabilities import CapabilityRegistry
from ..config import UnifiedGuiConfig
from ..panels import p5_permissions, p8_tickets
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
    registry.register(lock_adapter)
    registry.register(ticket_adapter)

    all_panels: list[PanelSpec] = [
        p5_permissions.build(lock_adapter),
        p8_tickets.build(ticket_adapter),
    ]

    app.state.config = config
    app.state.registry = registry
    app.state.all_panels = all_panels

    def visible_panels() -> list[PanelSpec]:
        return [p for p in all_panels if registry.supports(p.required)]

    guard = config.local_only if standalone_guard is None else standalone_guard
    if guard:
        app.add_middleware(LocalOnlyMiddleware)

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

    @app.post("/api/refresh")
    async def refresh():
        registry.refresh()
        return {
            "ok": True,
            "available": sorted(c.value for c in registry.available),
            "panels": [p.id for p in visible_panels()],
        }

    @app.get("/api/status")
    async def status():
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
