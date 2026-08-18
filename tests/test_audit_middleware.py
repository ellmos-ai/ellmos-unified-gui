# SPDX-License-Identifier: MIT
"""AuditMiddleware: isolierte Router-Tests (bare FastAPI + Middleware) plus
ein voller create_app()-Integrationstest, der beweist, dass die Verdrahtung
in web/app.py wirkt und eine echte Panel-Aktion (P11 create) weiterhin
funktioniert, WAEHREND die Middleware mitschreibt -- der Body-Caching-Punkt
aus dem Modul-Docstring ist eine Behauptung, die hier bewiesen wird."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.testclient import TestClient

from unified_gui.audit_middleware import AuditMiddleware, _outcome, _panel_and_action


class _FakeHostAuth:
    def __init__(self, user):
        self._user = user

    def current_user(self, request):
        return self._user


class _ThrowingHostAuth:
    def current_user(self, request):
        raise RuntimeError("boom")


class _Payload(BaseModel):
    name: str
    category: str


def _bare_app(auth_adapter=None, audit_log_path=None):
    app = FastAPI()
    app.add_middleware(AuditMiddleware, auth_adapter=auth_adapter, audit_log_path=audit_log_path)

    @app.get("/api/p9/skills")
    def read_only():
        return {"ok": True}

    @app.post("/api/p11/create")
    def write_action(payload: _Payload):
        return {"path": f"/fake/{payload.name}"}

    @app.post("/api/p5/rules")
    def denied_action():
        return JSONResponse({"detail": "nope"}, status_code=403)

    @app.post("/api/p5/locks/bulk-lock")
    def nested_action():
        return {"ok": True}

    @app.post("/api/refresh")
    def no_panel_prefix():
        return {"ok": True}

    return app


def test_panel_and_action_simple():
    assert _panel_and_action("/api/p11/create") == ("p11", "create")


def test_panel_and_action_nested():
    assert _panel_and_action("/api/p5/locks/bulk-lock") == ("p5", "locks/bulk-lock")


def test_panel_and_action_no_panel_prefix():
    assert _panel_and_action("/api/refresh") == (None, "refresh")


def test_outcome_buckets():
    assert _outcome(200) == "ok"
    assert _outcome(201) == "ok"
    assert _outcome(403) == "denied"
    assert _outcome(404) == "rejected"
    assert _outcome(500) == "error"


def test_read_only_requests_are_never_logged(tmp_path):
    target = tmp_path / "audit.jsonl"
    client = TestClient(_bare_app(audit_log_path=str(target)))
    resp = client.get("/api/p9/skills")
    assert resp.status_code == 200
    assert not target.exists()


def test_write_request_still_works_with_body_and_is_logged(tmp_path):
    """Der Beweis fuer den Body-Caching-Punkt aus dem Docstring: die
    Middleware liest den Body VOR call_next -- die echte Pydantic-Bindung im
    Endpunkt muss trotzdem den vollen Payload sehen, nicht nur einen Teil
    oder einen leeren Body."""
    target = tmp_path / "audit.jsonl"
    client = TestClient(_bare_app(audit_log_path=str(target)))
    resp = client.post("/api/p11/create", json={"name": "my-skill", "category": "dev"})
    assert resp.status_code == 200
    assert resp.json() == {"path": "/fake/my-skill"}  # Endpunkt sah den echten Body

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["panel"] == "p11"
    assert entry["action"] == "create"
    assert entry["method"] == "POST"
    assert entry["status_code"] == 200
    assert entry["outcome"] == "ok"
    assert sorted(entry["argument_keys"]) == ["category", "name"]
    assert "my-skill" not in json.dumps(entry)  # kein Argumentwert im Log
    assert "argument_values" not in entry


def test_denied_action_is_logged_too():
    """Deckt sich mit dem Vorbild: 'Jeder Aufruf, auch ein abgelehnter'."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "audit.jsonl"
        client = TestClient(_bare_app(audit_log_path=str(target)))
        resp = client.post("/api/p5/rules", json={"root": "x"})
        assert resp.status_code == 403
        entry = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
        assert entry["outcome"] == "denied"
        assert entry["status_code"] == 403


def test_nested_action_path_recorded():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "audit.jsonl"
        client = TestClient(_bare_app(audit_log_path=str(target)))
        client.post("/api/p5/locks/bulk-lock")
        entry = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
        assert entry["panel"] == "p5"
        assert entry["action"] == "locks/bulk-lock"


def test_role_and_user_captured_when_auth_adapter_present():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "audit.jsonl"
        auth = _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"})
        client = TestClient(_bare_app(auth_adapter=auth, audit_log_path=str(target)))
        client.post("/api/refresh")
        entry = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
        assert entry["user"] == "boss"
        assert entry["role"] == "admin"


def test_no_auth_adapter_role_and_user_are_null():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "audit.jsonl"
        client = TestClient(_bare_app(auth_adapter=None, audit_log_path=str(target)))
        client.post("/api/refresh")
        entry = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
        assert entry["user"] is None
        assert entry["role"] is None


def test_throwing_auth_adapter_never_breaks_the_real_response():
    """Load-bearing: ein Fehler in HostAuthAdapter.current_user() (Vertrags-
    verstoss, sollte nie werfen -- aber die Middleware darf sich nicht darauf
    verlassen) darf die echte Antwort nicht kaputt machen."""
    client = TestClient(_bare_app(auth_adapter=_ThrowingHostAuth()))
    resp = client.post("/api/refresh")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_audit_off_disables_logging_but_request_still_works():
    client = TestClient(_bare_app(audit_log_path="off"))
    resp = client.post("/api/refresh")
    assert resp.status_code == 200


def test_unwritable_audit_path_never_breaks_the_real_response(tmp_path):
    """Load-bearing: der zweite Sicherheitsfall -- append_audit_entry()
    scheitert (kaputter Pfad), die echte Antwort kommt trotzdem an."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    broken_path = str(blocker / "audit.jsonl")  # Elternteil ist eine Datei, kein Verzeichnis
    client = TestClient(_bare_app(audit_log_path=broken_path))
    resp = client.post("/api/p11/create", json={"name": "x", "category": "y"})
    assert resp.status_code == 200
    assert resp.json() == {"path": "/fake/x"}
