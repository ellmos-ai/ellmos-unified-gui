# SPDX-License-Identifier: MIT
"""P13 Chat: minimaler Durchstich fuer ellmos-chat als chat.runtime-Provider
(Wheelhouse M1, T-20260825-835413946).

v1-Scope (bewusst klein, laut Ticket "kein Vollausbau"): eine Frage rein,
eine Antwort raus -- kein Verlaufs-UI, keine Modellwahl, kein
Tool-Konfigurator im Panel selbst (ellmos-chat haelt seinen eigenen Store
und seine eigene SafetyPolicy). Naechste Ausbaustufen (Streaming, Modellwahl,
Session-Liste) sind bewusst NICHT Teil dieses Sub-Tickets.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.base import AdapterError
from ..adapters.ellmos_chat import EllmosChatAdapter
from ..capabilities import Capability
from .base import PanelSpec


class AskRequest(BaseModel):
    text: str
    chat_id: str = "unified-gui"


def build(adapter: EllmosChatAdapter) -> PanelSpec:
    router = APIRouter()

    @router.post("/api/p13/ask")
    async def ask(body: AskRequest):
        try:
            return await adapter.ask(body.text, body.chat_id)
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    return PanelSpec(
        id="p13",
        label="Chat",
        path="/p13",
        template="p13_chat.html",
        required={Capability.CHAT_RUNTIME},
        router=router,
    )
