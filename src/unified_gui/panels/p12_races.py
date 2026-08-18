# SPDX-License-Identifier: MIT
"""P12 Races: read-only Browser fuer compare-race-Ergebnisse.

Bewusst nur Lesen (siehe adapters/compare_race.py-Docstring fuer die
Begruendung) -- kein "Race starten"-Knopf, kein Judge-Trigger.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..adapters.base import AdapterError
from ..adapters.compare_race import CompareRaceAdapter
from ..capabilities import Capability
from .base import PanelSpec


def build(adapter: CompareRaceAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p12/races")
    def races():
        return _guard(adapter.races)

    @router.get("/api/p12/races/{race_id}")
    def race_detail(race_id: str):
        return _guard(lambda: adapter.race_detail(race_id))

    return PanelSpec(
        id="p12",
        label="Races",
        path="/p12",
        template="p12_races.html",
        required={Capability.RACES_RO},
        router=router,
    )
