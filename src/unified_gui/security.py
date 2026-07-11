# SPDX-License-Identifier: MIT
"""Standalone-Guard: nur lokale Clients + Origin-Check auf schreibenden Methoden.

Muster: lock-master-Watcher (Local-Origin-Guard). Gilt NUR im Standalone-Betrieb;
im Mount-Betrieb ist Auth/Zugriff Sache des Hosts (ARCHITECTURE.md).
"""
from __future__ import annotations

from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# "testclient" = starlette TestClient (nur in Tests relevant, kein Netz-Zugang)
_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class LocalOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else ""
        if client not in _LOCAL_HOSTS:
            return JSONResponse({"detail": "Nur lokale Zugriffe erlaubt"}, status_code=403)
        if request.method in _WRITE_METHODS:
            origin = request.headers.get("origin")
            if origin:
                host = urlparse(origin).hostname or ""
                if host not in _LOCAL_HOSTS:
                    return JSONResponse({"detail": "Origin nicht erlaubt"}, status_code=403)
        return await call_next(request)
