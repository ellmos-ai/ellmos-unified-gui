# SPDX-License-Identifier: MIT
"""P10 Decisions: read-only Sicht auf den TO-DECIDE-Index (decisions.index.json).

Nur GET-Endpunkte -- kein POST/PUT/DELETE, kein Schreibpfad. Die Wahrheit
bleibt bei den TO-DECIDE-*.txt-Quelldateien und dem Index-Generator unter
_control-center/_DECISIONS/_tools/; dieses Panel liest ausschliesslich den
bereits erzeugten Index ueber DecisionsAdapter, nie die Quelldateien selbst.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..adapters.base import AdapterError
from ..adapters.decisions import DecisionsAdapter
from ..capabilities import Capability
from .base import PanelSpec


def build(adapter: DecisionsAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p10/summary")
    def summary():
        return _guard(adapter.summary)

    @router.get("/api/p10/entries")
    def entries(scope: str | None = None, status_class: str | None = None):
        rows = _guard(lambda: adapter.entries(scope=scope, status_class=status_class))
        return {"entries": rows, "count": len(rows)}

    return PanelSpec(
        id="p10",
        label="Decisions",
        path="/p10",
        template="p10_decisions.html",
        required={Capability.DECISIONS_RO},
        router=router,
    )
