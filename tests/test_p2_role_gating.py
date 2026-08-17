# SPDX-License-Identifier: MIT
"""P2 Rollen-Gating: Agenten starten/stoppen/steuern/checkpointen nur fuer
'admin', wenn eine Host-Session mit Rolle tatsaechlich vorliegt (ellmos-core-
Mount-Betrieb) — sonst exakt das bisherige Verhalten. Zweites Panel nach P5,
gleiches Muster (siehe adapters/host_auth.py + panels/p2_agents.py).

Nutzt ein Fake-BachAdapter-Doppel statt echtem BACH -- P2 hatte vor diesem
Durchgang keine eigene Testsuite; dieser Test deckt zusaetzlich zum Gating
erstmals ab, dass die Schreibpfade den Adapter ueberhaupt korrekt aufrufen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI
from starlette.testclient import TestClient

from unified_gui.panels import p2_agents


class _FakeHostAuth:
    def __init__(self, user: dict | None) -> None:
        self._user = user

    def current_user(self, request):
        return self._user


class _FakeBachAdapter:
    """Minimaler Stand-in fuer BachAdapter -- zaehlt Aufrufe statt echtes
    BACH-CLI anzusprechen (P2 hat kein CLI-Fixture, anders als lock-master)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def agents(self):
        return {"agents": [{"name": "buero"}]}

    def agent_start(self, name, model=None, mode=None):
        self.calls.append(("start", name))
        return {"ok": True, "name": name}

    def agent_stop(self, name):
        self.calls.append(("stop", name))
        return {"ok": True, "name": name}

    def agent_steer(self, name, note):
        self.calls.append(("steer", name, note))
        return {"ok": True, "name": name}

    def agent_clear_steer(self, name):
        self.calls.append(("clear-steer", name))
        return {"ok": True, "name": name}

    def agent_checkpoint(self, name):
        self.calls.append(("checkpoint", name))
        return {"ok": True, "name": name}


def _client_for(bach_adapter, auth_adapter):
    app = FastAPI()
    spec = p2_agents.build(bach_adapter, auth_adapter)
    app.include_router(spec.router)
    return TestClient(app)


def test_no_auth_adapter_writes_unchanged():
    bach = _FakeBachAdapter()
    client = _client_for(bach, None)
    resp = client.post("/api/p2/start", json={"name": "buero"})
    assert resp.status_code == 200
    assert ("start", "buero") in bach.calls


def test_auth_adapter_present_but_no_session_writes_unchanged():
    bach = _FakeBachAdapter()
    client = _client_for(bach, _FakeHostAuth(None))
    resp = client.post("/api/p2/stop", json={"name": "buero"})
    assert resp.status_code == 200
    assert ("stop", "buero") in bach.calls


def test_non_admin_role_is_forbidden_from_start():
    bach = _FakeBachAdapter()
    client = _client_for(bach, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.post("/api/p2/start", json={"name": "buero"})
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]
    assert bach.calls == []  # nie beim Adapter angekommen


def test_non_admin_role_is_forbidden_from_stop_steer_checkpoint():
    bach = _FakeBachAdapter()
    client = _client_for(bach, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    assert client.post("/api/p2/stop", json={"name": "buero"}).status_code == 403
    assert client.post("/api/p2/steer", json={"name": "buero", "note": "weiter so"}).status_code == 403
    assert client.post("/api/p2/clear-steer", json={"name": "buero"}).status_code == 403
    assert client.post("/api/p2/checkpoint", json={"name": "buero"}).status_code == 403
    assert bach.calls == []


def test_admin_role_may_write():
    bach = _FakeBachAdapter()
    client = _client_for(bach, _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"}))
    resp = client.post("/api/p2/start", json={"name": "buero"})
    assert resp.status_code == 200
    assert ("start", "buero") in bach.calls


def test_reads_stay_open_regardless_of_role():
    bach = _FakeBachAdapter()
    client = _client_for(bach, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.get("/api/p2/agents")
    assert resp.status_code == 200
