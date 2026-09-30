# SPDX-License-Identifier: MIT
"""Explicit optional consumer of the BACH-derived neutral Activity shell.

The Lite factory remains independent: the neutral package is loaded only when
this factory is explicitly called. Backend calls remain in the shared browser
client; no proxy, credential store, worker or discovery is created here.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..security import LocalOnlyMiddleware


def create_control_shell_app(
    *, control_api: str | None = None, branding: dict[str, Any] | None = None,
    read_only: bool = True, renderer: Callable[..., str] | None = None,
    standalone_guard: bool = True,
) -> FastAPI:
    """Serve shared resources; RW additionally requires backend auth per command.

    ``control_api`` identifies an existing browser-reachable Control API.
    The host owns its auth/origin policy. Cross-origin servers must explicitly
    permit the browser origin; this consumer does not relax backend policy.
    """
    if not isinstance(read_only, bool):
        raise ValueError("read_only muss ein boolescher Wert sein")
    if not read_only and not control_api:
        raise ValueError("Schreibzugriff benötigt eine explizite Control-API")
    if renderer is None:
        from ocean_gui_shell import render_activity_dashboard
        renderer = render_activity_dashboard
    cfg = deepcopy(branding or {})
    cfg["read_only"] = read_only
    api_base = control_api or "/__control_backend_unconfigured__/api"
    # Validate config before registering routes; the renderer is side-effect free.
    renderer(cfg, api_base=api_base)
    app = FastAPI(title=cfg.get("title", "OCEAN Aktivitäten & Worker"), docs_url=None, redoc_url=None)
    if standalone_guard:
        app.add_middleware(LocalOnlyMiddleware)

    @app.get("/", include_in_schema=False)
    def index(request: Request):
        return RedirectResponse(request.scope.get("root_path", "") + "/activity", status_code=302)

    @app.get("/activity", response_class=HTMLResponse, include_in_schema=False)
    def activity(request: Request):
        page_cfg = deepcopy(cfg)
        if "nav_links" not in page_cfg:
            page_cfg["nav_links"] = [{"label": "Übersicht", "href": request.scope.get("root_path", "") + "/"}]
        return HTMLResponse(renderer(page_cfg, api_base=api_base))

    return app


def mount_control_shell(host_app: FastAPI, prefix: str = "/ocean", **options: Any) -> FastAPI:
    """Mount the optional neutral shell; host auth protects this sub-app."""
    options["standalone_guard"] = False
    app = create_control_shell_app(**options)
    host_app.mount(prefix, app)
    return app
