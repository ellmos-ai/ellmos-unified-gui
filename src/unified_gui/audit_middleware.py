# SPDX-License-Identifier: MIT
"""AuditMiddleware: loggt jede zustandsaendernde Anfrage an die Konsole ueber
`audit_log.py` (siehe dessen Docstring fuer das Vorbild und die bewussten
Abweichungen davon).

Registriert in `web/app.py::create_app()` -- wirkt dadurch automatisch sowohl
standalone (`python -m unified_gui`) als auch eingehaengt (`mount()` ruft
`create_app()` intern auf, siehe dessen Docstring "Auth uebernimmt der
Host"). Deckt so JEDEN Panel-Schreibpfad ab, auch kuenftige, ohne
Panel-fuer-Panel-Nacharbeit -- statt die drei heute rollen-gegateten Panels
(P2/P5/P11) einzeln zu verdrahten, greift die Middleware auf HTTP-Ebene:
schreibende Methoden sind in diesem Repo durchgaengig POST/PUT/PATCH/DELETE
(dieselbe Menge, die `security.LocalOnlyMiddleware` bereits fuer den
Origin-Check verwendet -- hier wiederverwendet, nicht dupliziert).

Sicherheitsregel, staerker als beim Vorbild: ein Fehler in DIESEM Modul darf
niemals eine echte Konsolen-Aktion verhindern. `dispatch()` faengt deshalb
jeden eigenen Fehler ab, BEVOR die Antwort zurueckgegeben wird -- eine
interaktive Schreibaktion (P5-Regel aendern, P11-Skill anlegen) soll nie an
einem Logging-Bug scheitern. Siehe test_audit_middleware.py fuer den Beweis,
nicht nur die Behauptung.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware

from .audit_log import append_audit_entry
from .security import _WRITE_METHODS

if TYPE_CHECKING:  # pragma: no cover
    from starlette.requests import Request
    from starlette.responses import Response

    from .adapters.host_auth import HostAuthAdapter


def _panel_and_action(path: str) -> tuple[str | None, str]:
    """"/api/p11/create" -> ("p11", "create"); "/api/p5/locks/bulk-lock" ->
    ("p5", "locks/bulk-lock"); "/api/refresh" (kein Panel-Praefix) ->
    (None, "refresh")."""
    parts = [p for p in path.split("/") if p]
    if parts and parts[0] == "api":
        parts = parts[1:]
    if len(parts) >= 2 and parts[0].startswith("p") and parts[0][1:].isdigit():
        return parts[0], "/".join(parts[1:])
    return None, "/".join(parts) or path


def _outcome(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "ok"
    if status_code == 403:
        return "denied"
    if 400 <= status_code < 500:
        return "rejected"
    return "error"


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_adapter: "HostAuthAdapter | None" = None,
                 audit_log_path: str | None = None) -> None:
        super().__init__(app)
        self._auth_adapter = auth_adapter
        self._audit_log_path = audit_log_path

    async def dispatch(self, request: "Request", call_next) -> "Response":
        if request.method not in _WRITE_METHODS:
            return await call_next(request)

        started = time.monotonic()
        argument_keys = await self._safe_argument_keys(request)
        user = self._safe_current_user(request)
        response = await call_next(request)

        try:
            panel, action = _panel_and_action(request.url.path)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "panel": panel,
                "action": action,
                "user": user.get("username") if user else None,
                "role": user.get("role") if user else None,
                "status_code": response.status_code,
                "outcome": _outcome(response.status_code),
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
                "argument_keys": argument_keys,
            }
            append_audit_entry(entry, self._audit_log_path)
        except Exception:  # noqa: BLE001 -- Audit darf die echte Antwort nie verhindern
            pass
        return response

    @staticmethod
    async def _safe_argument_keys(request: "Request") -> list[str]:
        """Liest den Body (cached fuer nachgelagerte Pydantic-Parses, siehe
        Starlette Request.body()) und meldet NUR die Top-Level-Schluessel --
        nie die Werte. Kein JSON-Body (leer, Formular, kaputt) -> leere Liste,
        kein Fehler."""
        try:
            body = await request.body()
            if not body:
                return []
            data = json.loads(body)
            return sorted(data.keys()) if isinstance(data, dict) else []
        except Exception:  # noqa: BLE001
            return []

    def _safe_current_user(self, request: "Request") -> dict[str, Any] | None:
        if self._auth_adapter is None:
            return None
        try:
            return self._auth_adapter.current_user(request)
        except Exception:  # noqa: BLE001 -- HostAuthAdapter.probe()-Vertrag: nie werfen
            return None
