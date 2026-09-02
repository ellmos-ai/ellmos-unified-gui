# SPDX-License-Identifier: MIT
"""P15 Nachrichten: Auftragsnachrichten an Agenten und deren Antworten.

Konsumiert die BACH-REST-Endpunkte ``/api/messages*`` über den BachAdapter —
seit Welle 1 des BACH-GUI-Modulschnitts (D-20260830-002) laufen die dort über
``assistant_core.MessageStore``; Datenhoheit bleibt bei ``bach.db`` (D04),
das Panel hält nichts selbst und greift nie direkt auf ein Backend zu (D03).

Eine Antwort ist eine ``inbox``-Nachricht, deren ``parent_id`` auf den
Auftrag zeigt — das Panel zeigt den Link, erfindet keinen Status.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters.bach import BachAdapter
from ..adapters.base import AdapterError
from ..capabilities import Capability
from .base import PanelSpec


class MessageCreateRequest(BaseModel):
    recipient: str
    body: str
    subject: str | None = None
    priority: int = 0


def build(bach: BachAdapter) -> PanelSpec:
    router = APIRouter()

    def _guard(fn):
        try:
            return fn()
        except AdapterError as exc:
            raise HTTPException(status_code=409, detail=f"{exc.kind}: {exc.hint}") from exc

    @router.get("/api/p15/messages")
    def list_messages(direction: str | None = None, status: str | None = None,
                      partner: str | None = None, include_archived: bool = True, limit: int = 50):
        rows = _guard(lambda: bach.messages(direction=direction, status=status, partner=partner,
                                             include_archived=include_archived, limit=limit))
        return {"messages": rows, "count": len(rows)}

    @router.post("/api/p15/messages")
    def create_message(req: MessageCreateRequest):
        if not req.recipient.strip() or not req.body.strip():
            raise HTTPException(status_code=400, detail="Empfänger und Text sind Pflicht")
        return _guard(lambda: bach.message_create(req.recipient.strip(), req.body, subject=req.subject,
                                                  priority=req.priority))

    @router.post("/api/p15/messages/{msg_id}/read")
    def mark_read(msg_id: int):
        return _guard(lambda: bach.message_mark_read(msg_id))

    @router.post("/api/p15/messages/mark-all-read")
    def mark_all_read():
        return _guard(bach.message_mark_all_read)

    @router.post("/api/p15/messages/{msg_id}/archive")
    def archive(msg_id: int):
        return _guard(lambda: bach.message_archive(msg_id))

    @router.post("/api/p15/messages/{msg_id}/delete")
    def delete(msg_id: int):
        return _guard(lambda: bach.message_delete(msg_id))

    return PanelSpec(
        id="p15",
        label="Nachrichten",
        path="/p15",
        template="p15_messages.html",
        required={Capability.MESSAGES_RW},
        router=router,
    )
