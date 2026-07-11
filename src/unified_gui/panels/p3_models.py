# SPDX-License-Identifier: MIT
"""P3 Modelle: clutch-Gears (lokal + API-Provider) und Ollama-Live-Sicht.

Credentials bleiben in clutchs Store (~/.clutch/credentials.json via
`clutch keys`) — die GUI zeigt nur Provider/Kosten/Staerken, NIE Schluessel.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..adapters.base import AdapterError
from ..adapters.clutch import ClutchAdapter
from ..adapters.ollama import OllamaAdapter
from ..capabilities import Capability, CapabilityRegistry
from .base import PanelSpec


def build(clutch: ClutchAdapter, ollama: OllamaAdapter,
          registry: CapabilityRegistry) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p3/models")
    def models():
        sources = []
        entries: list[dict] = []
        for adapter in (clutch, ollama):
            state = next((s for s in registry.states if s.adapter is adapter), None)
            available = state is not None and bool(state.capabilities)
            entry = {"name": adapter.name, "available": available, "error": None, "count": 0}
            if available:
                try:
                    rows = adapter.models()
                    entry["count"] = len(rows)
                    entries.extend(rows)
                except AdapterError as exc:
                    entry["error"] = f"{exc.kind}: {exc.hint}"
            sources.append(entry)
        return {"models": entries, "sources": sources}

    @router.get("/api/p3/running")
    def running():
        return {"running": _guard(ollama.running)}

    return PanelSpec(
        id="p3",
        label="Modelle",
        path="/p3",
        template="p3_models.html",
        required={Capability.MODELS_LOCAL},
        router=router,
    )
