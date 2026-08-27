# SPDX-License-Identifier: MIT
"""P14 Governance: fertigen ControlCenter-Lesespiegel rein lesend anzeigen."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..adapters.base import AdapterError
from ..adapters.controlcenter import ControlCenterAdapter
from ..capabilities import Capability
from .base import PanelSpec


def build(adapter: ControlCenterAdapter) -> PanelSpec:
    router = APIRouter()

    @router.get("/api/p14/governance")
    def governance():
        try:
            return adapter.governance()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    return PanelSpec(
        id="p14",
        label="Governance",
        path="/p14",
        template="p14_governance.html",
        required={Capability.GOVERNANCE_RO},
        router=router,
    )
