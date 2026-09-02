# SPDX-License-Identifier: MIT
"""P15 Nachrichten: Auftragsnachrichten nur über den BachAdapter (BACH-REST /api/messages*).

Welle 1 Teil 2b des BACH-GUI-Modulschnitts (D-20260830-002): dieselbe Fachlogik wie
BACHs ``assistant_core.MessageStore``, konsumiert über REST — kein eigener Store (D04),
kein Backend-Direktzugriff aus dem Panel (D03), Schreibaktionen werden zurückgelesen.
"""
from __future__ import annotations

import sys
from pathlib import Path

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unified_gui.adapters.bach import BachAdapter  # noqa: E402
from unified_gui.adapters.base import AdapterError  # noqa: E402
from unified_gui.capabilities import Capability, HealthInfo  # noqa: E402
from unified_gui.config import BachConfig  # noqa: E402
from unified_gui.web import app as app_module  # noqa: E402


class FakeBachAdapter:
    """In-memory Doppel der BACH-REST-Nachrichten; Semantik wie assistant_core.MessageStore."""

    name = "bach"
    label = "BACH (fake)"
    capabilities = {Capability.MESSAGES_RW, Capability.TASKS_RO}
    rows: list[dict] = []

    def __init__(self, _config=None) -> None:
        pass

    def probe(self):
        return set(self.capabilities)

    def health(self):
        return HealthInfo("ok", "fake")

    def messages(self, direction=None, status=None, partner=None, include_archived=True, limit=50):
        out = [r for r in self.rows if r["status"] != "deleted"]
        if direction:
            out = [r for r in out if r["direction"] == direction]
        if status:
            out = [r for r in out if r["status"] == status]
        elif not include_archived:
            out = [r for r in out if r["status"] != "archived"]
        if partner:
            out = [r for r in out if partner in (r["sender"], r["recipient"])]
        return list(reversed(out))[:limit]

    def message_create(self, recipient, body, subject=None, priority=0):
        row = {"id": len(self.rows) + 1, "direction": "outbox", "sender": "user", "recipient": recipient,
               "subject": subject, "body": body, "priority": priority, "status": "unread", "parent_id": None}
        self.rows.append(row)
        return {"id": row["id"], "status": "created"}

    def _set(self, msg_id, status):
        for r in self.rows:
            if r["id"] == msg_id:
                r["status"] = status
                return {"status": status}
        raise AdapterError("not-found", f"#{msg_id}")

    def message_mark_read(self, msg_id):
        return self._set(msg_id, "read")

    def message_mark_all_read(self):
        marked = sum(1 for r in self.rows if r["status"] == "unread")
        for r in self.rows:
            if r["status"] == "unread":
                r["status"] = "read"
        return {"status": "ok", "marked": marked}

    def message_archive(self, msg_id):
        return self._set(msg_id, "archived")

    def message_delete(self, msg_id):
        return self._set(msg_id, "deleted")


def _client(monkeypatch, capabilities=None):
    FakeBachAdapter.rows = []
    FakeBachAdapter.capabilities = capabilities or {Capability.MESSAGES_RW, Capability.TASKS_RO}
    monkeypatch.setattr(app_module, "BachAdapter", FakeBachAdapter)
    return TestClient(app_module.create_app(config={}, standalone_guard=False))


def test_panel_visible_only_with_messages_capability(monkeypatch):
    client = _client(monkeypatch)
    status = client.get("/api/status").json()
    assert "p15" in status["panels"] and "messages.rw" in status["available"]

    client = _client(monkeypatch, capabilities={Capability.TASKS_RO})
    status = client.get("/api/status").json()
    assert "p15" not in status["panels"]


def test_create_is_read_back_and_actions_change_status(monkeypatch):
    client = _client(monkeypatch)
    created = client.post("/api/p15/messages", json={"recipient": "ollama", "body": "Fasse zusammen",
                                                     "subject": "Digest"}).json()
    assert created == {"id": 1, "status": "created"}
    listed = client.get("/api/p15/messages?direction=outbox").json()
    assert listed["count"] == 1 and listed["messages"][0]["recipient"] == "ollama"

    assert client.post("/api/p15/messages/1/read").json() == {"status": "read"}
    assert client.get("/api/p15/messages?status=read").json()["count"] == 1
    assert client.post("/api/p15/messages/1/archive").json() == {"status": "archived"}
    assert client.get("/api/p15/messages?include_archived=false").json()["count"] == 0
    assert client.post("/api/p15/messages/1/delete").json() == {"status": "deleted"}
    assert client.get("/api/p15/messages").json()["count"] == 0


def test_mark_all_read_and_validation(monkeypatch):
    client = _client(monkeypatch)
    client.post("/api/p15/messages", json={"recipient": "bach", "body": "a"})
    client.post("/api/p15/messages", json={"recipient": "buddha", "body": "b"})
    assert client.post("/api/p15/messages/mark-all-read").json() == {"status": "ok", "marked": 2}
    assert client.post("/api/p15/messages", json={"recipient": " ", "body": "x"}).status_code == 400
    assert client.post("/api/p15/messages/99/read").status_code == 409  # AdapterError -> Inline-Hinweis, nie 500


def test_bach_adapter_maps_rest_messages(monkeypatch):
    adapter = BachAdapter(BachConfig())
    calls = []

    def fake_rest(path, method="GET", payload=None):
        calls.append((method, path, payload))
        if path.startswith("/api/messages?"):
            return {"messages": [{"id": 7, "direction": "inbox", "sender": "ollama", "recipient": "user",
                                  "body": "4", "status": "unread", "parent_id": 3}], "count": 1}
        if path == "/api/messages":
            return {"id": 8, "status": "created"}
        if path == "/api/messages/mark-all-read":
            return {"status": "ok", "marked": 1}
        return {"status": path.rsplit("/", 1)[-1]}

    monkeypatch.setattr(adapter, "_rest", fake_rest)

    rows = adapter.messages(direction="inbox", partner="ollama", limit=10)
    assert rows[0]["parent_id"] == 3 and rows[0]["sender"] == "ollama"
    assert adapter.message_create("ollama", "Was ist 2+2?", subject="Rechnen", priority=1) == {"id": 8, "status": "created"}
    assert adapter.message_mark_read(7) == {"status": "read"}
    assert adapter.message_archive(7) == {"status": "archive"}
    assert adapter.message_delete(7) == {"status": "delete"}
    assert adapter.message_mark_all_read() == {"status": "ok", "marked": 1}
    assert calls[0] == ("GET", "/api/messages?direction=inbox&partner=ollama&include_archived=true&limit=10", None)
    assert calls[1] == ("POST", "/api/messages", {"recipient": "ollama", "subject": "Rechnen", "body": "Was ist 2+2?", "priority": 1})
    assert calls[2] == ("PUT", "/api/messages/7/read", None)


def test_probe_reports_messages_only_with_rest(monkeypatch):
    adapter = BachAdapter(BachConfig())
    monkeypatch.setattr(adapter, "_probe_rest", lambda: True)
    monkeypatch.setattr(adapter, "_system_dir", lambda: None)
    assert Capability.MESSAGES_RW in adapter.probe()
    monkeypatch.setattr(adapter, "_probe_rest", lambda: False)
    assert Capability.MESSAGES_RW not in adapter.probe()


def test_template_renders_untrusted_text_safely_and_explains_data_ownership():
    template = (Path(__file__).parent.parent / "src" / "unified_gui" / "web" / "templates"
                / "p15_messages.html").read_text(encoding="utf-8")
    assert "textContent = text(m.body)" in template
    assert "innerHTML" not in template
    assert "Daten bleiben in BACH" in template
    assert "/api/p15/messages" in template
