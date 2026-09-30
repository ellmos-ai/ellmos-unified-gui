# SPDX-License-Identifier: MIT
"""Vertragstests für den Control-API (:8081) Adapter in BachAdapter (T-20260926-652455601).

Testet:
- Konfigurations-Kaskade (Defaults, Overrides, Environment-Variablen, Token-Files)
- Capability-Gating & Probing (CONTROL_API, CONTROL_SLOTS_RO, CONTROL_WORKERS_RW, CONTROL_ACTIVITY_RO)
- Health-Reporting (ok, degraded, offline)
- Bearer-Token-Header & Authentifizierungsfehler (401, 403, 409)
- Getypte Methoden (control_status, control_readiness, control_slots, control_workers, control_activity,
  control_create_worker, control_delete_worker, control_toggle_worker, control_stop_worker, control_run_worker)
- Robuste Fehlerbehandlung (Unreachable, Bad JSON)
"""
from __future__ import annotations

import io
import sys
import threading
import time
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unified_gui.adapters.bach import BachAdapter
from unified_gui.adapters.base import AdapterError
from unified_gui.capabilities import Capability
from unified_gui.config import BachConfig, UnifiedGuiConfig


# ======================================================================
# 1. Konfiguration
# ======================================================================

def test_bach_config_control_defaults():
    cfg = BachConfig()
    assert cfg.control_url == "http://127.0.0.1:8081"
    assert cfg.control_timeout_s == 2.0
    assert cfg.control_token is None
    assert cfg.control_token_file is None


def test_bach_config_control_overrides():
    app_cfg = UnifiedGuiConfig.load(
        overrides={
            "bach": {
                "control_url": "http://127.0.0.1:8099",
                "control_timeout_s": 5.0,
                "control_token": "my-secret-token",
            }
        }
    )
    assert app_cfg.bach.control_url == "http://127.0.0.1:8099"
    assert app_cfg.bach.control_timeout_s == 5.0
    assert app_cfg.bach.control_token == "my-secret-token"


def test_bach_config_control_env(monkeypatch):
    monkeypatch.setenv("UNIFIED_GUI_BACH_CONTROL_URL", "http://localhost:8181")
    monkeypatch.setenv("UNIFIED_GUI_BACH_CONTROL_TOKEN", "env-token-xyz")
    app_cfg = UnifiedGuiConfig.load()
    assert app_cfg.bach.control_url == "http://localhost:8181"
    assert app_cfg.bach.control_token == "env-token-xyz"


def test_token_resolution_order(tmp_path, monkeypatch):
    token_file = tmp_path / "token.txt"
    token_file.write_text("file-token-123\n", encoding="utf-8")

    # 1. Config explicit token wins over file and env
    cfg1 = BachConfig(control_token="explicit-token", control_token_file=str(token_file))
    adapter1 = BachAdapter(cfg1)
    assert adapter1._resolve_control_token() == "explicit-token"

    # 2. Config token file wins over env
    monkeypatch.setenv("BACH_CONTROL_API_TOKEN", "env-token")
    cfg2 = BachConfig(control_token_file=str(token_file))
    adapter2 = BachAdapter(cfg2)
    assert adapter2._resolve_control_token() == "file-token-123"

    # 3. Environment token is used when config fields are None
    cfg3 = BachConfig()
    adapter3 = BachAdapter(cfg3)
    assert adapter3._resolve_control_token() == "env-token"

    # 4. Environment token file
    monkeypatch.delenv("BACH_CONTROL_API_TOKEN")
    monkeypatch.setenv("BACH_CONTROL_API_TOKEN_FILE", str(token_file))
    adapter4 = BachAdapter(BachConfig())
    assert adapter4._resolve_control_token() == "file-token-123"

    # 5. Missing token returns None
    monkeypatch.delenv("BACH_CONTROL_API_TOKEN_FILE")
    adapter5 = BachAdapter(BachConfig())
    assert adapter5._resolve_control_token() is None


# ======================================================================
# 2. Probing & Capability Gating
# ======================================================================

def test_probe_control_api_offline():
    adapter = BachAdapter(
        BachConfig(
            bach_root="/nonexistent",
            rest_url="http://127.0.0.1:1",
            rest_timeout_s=0.1,
            control_url="http://127.0.0.1:1",
            control_timeout_s=0.1,
        )
    )
    caps = adapter.probe()
    assert Capability.CONTROL_API not in caps
    assert Capability.CONTROL_SLOTS_RO not in caps
    assert Capability.CONTROL_WORKERS_RW not in caps
    assert Capability.CONTROL_ACTIVITY_RO not in caps
    assert adapter.health().status == "offline"


def test_probe_control_api_online(monkeypatch):
    adapter = BachAdapter(
        BachConfig(
            bach_root="/nonexistent",
            rest_url="http://127.0.0.1:1",
            rest_timeout_s=0.1,
            control_url="http://127.0.0.1:8081",
        )
    )

    def fake_control(path, method="GET", payload=None):
        if path == "/api/status":
            return {"service": "bach-chat-control", "model": "qwen"}
        if path == "/api/slots":
            return {"slots": {}}
        if path == "/api/activity?limit=0":
            return {"history": []}
        raise AdapterError("bach_control_not_found", path)

    monkeypatch.setattr(adapter, "_control", fake_control)
    caps = adapter.probe()
    assert Capability.CONTROL_API in caps
    assert Capability.CONTROL_SLOTS_RO in caps
    assert Capability.CONTROL_WORKERS_RW not in caps
    assert Capability.CONTROL_ACTIVITY_RO in caps
    # REST is offline, CLI is offline -> status is degraded because only Control-API is online
    assert adapter.health().status == "degraded"
    assert "Control-API erreichbar" in adapter.health().detail


# ======================================================================
# 3. Transport & Bearer Token Headers
# ======================================================================

def test_control_request_attaches_bearer_token(monkeypatch):
    adapter = BachAdapter(BachConfig(control_token="secret-bearer-123"))
    recorded_requests = []

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=None):
        recorded_requests.append(req)
        return DummyResponse()

    monkeypatch.setattr(adapter._control_opener, "open", fake_urlopen)
    res = adapter._control("/api/test", method="POST", payload={"data": 1})
    assert res == {"ok": True}
    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert req.get_header("Authorization") == "Bearer secret-bearer-123"
    assert req.get_header("Content-type") == "application/json"


def test_control_request_handles_401_unauthorized(monkeypatch):
    adapter = BachAdapter(BachConfig())

    def fake_urlopen(req, timeout=None):
        fp = io.BytesIO(b'{"error": "Control-API-Token erforderlich"}')
        raise urllib.error.HTTPError("http://127.0.0.1:8081/api/workers/run", 401, "Unauthorized", {}, fp)

    monkeypatch.setattr(adapter._control_opener, "open", fake_urlopen)
    with pytest.raises(AdapterError) as exc_info:
        adapter._control("/api/workers/run", method="POST", payload={"id": "w1"})
    assert exc_info.value.kind == "bach_control_unauthorized"


def test_control_request_handles_409_conflict(monkeypatch):
    adapter = BachAdapter(BachConfig())

    def fake_urlopen(req, timeout=None):
        fp = io.BytesIO(b'{"error": "Worker laeuft bereits"}')
        raise urllib.error.HTTPError("http://127.0.0.1:8081/api/workers/run", 409, "Conflict", {}, fp)

    monkeypatch.setattr(adapter._control_opener, "open", fake_urlopen)
    with pytest.raises(AdapterError) as exc_info:
        adapter._control("/api/workers/run", method="POST", payload={"id": "w1"})
    assert exc_info.value.kind == "bach_control_conflict"


def test_control_request_handles_bad_json(monkeypatch):
    adapter = BachAdapter(BachConfig())

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b"<html>Not JSON</html>"

    monkeypatch.setattr(adapter._control_opener, "open", lambda req, timeout=None: DummyResponse())
    with pytest.raises(AdapterError) as exc_info:
        adapter._control("/api/status")
    assert exc_info.value.kind == "bach_control_bad_json"


# ======================================================================
# 4. Getypte Control-API Methoden
# ======================================================================

def test_control_status_and_readiness(monkeypatch):
    adapter = BachAdapter(BachConfig())
    calls = []

    def fake_control(path, method="GET", payload=None):
        calls.append((path, method, payload))
        if path == "/api/status":
            return {"service": "bach-chat-control", "sessions": 3}
        if path.startswith("/api/readiness"):
            return {"available": True, "status": "ok", "backend_id": "ollama"}
        return {}

    monkeypatch.setattr(adapter, "_control", fake_control)

    status = adapter.control_status()
    assert status["service"] == "bach-chat-control"
    assert calls[-1] == ("/api/status", "GET", None)

    readiness = adapter.control_readiness("worker-alpha")
    assert readiness["available"] is True
    assert calls[-1] == ("/api/readiness?chat_id=worker-alpha", "GET", None)


def test_control_slots_and_workers(monkeypatch):
    adapter = BachAdapter(BachConfig())
    calls = []

    def fake_control(path, method="GET", payload=None):
        calls.append((path, method, payload))
        if path == "/api/slots":
            return {
                "ok": True,
                "slots": {"tg:1": {"name": "Slot 1"}},
                "dynamic_workers": [{"id": "w1", "name": "Worker 1"}],
            }
        if path == "/api/workers":
            return {"ok": True, "workers": [{"id": "w1", "name": "Worker 1"}]}
        return {}

    monkeypatch.setattr(adapter, "_control", fake_control)

    slots_data = adapter.control_slots()
    assert slots_data["ok"] is True
    assert "slots" in slots_data

    workers = adapter.control_workers()
    assert len(workers) == 1
    assert workers[0]["id"] == "w1"


def test_control_activity_query_formatting(monkeypatch):
    adapter = BachAdapter(BachConfig())
    recorded_path = []

    def fake_control(path, method="GET", payload=None):
        recorded_path.append(path)
        return {
            "ok": True,
            "history": [
                {"id": 1, "source": "system", "text": "Activity 1", "status": "ok"}
            ],
        }

    monkeypatch.setattr(adapter, "_control", fake_control)

    # Mit Filter-Listen
    history = adapter.control_activity(
        limit=25,
        offset=10,
        source=["worker-1", "system"],
        status=["ok", "error"],
        order="asc",
    )
    assert len(history) == 1
    assert len(recorded_path) == 1
    path = recorded_path[0]
    assert "/api/activity?" in path
    assert "limit=25" in path
    assert "offset=10" in path
    assert "order=asc" in path
    assert "source=worker-1%2Csystem" in path
    assert "status=ok%2Cerror" in path


def test_control_worker_lifecycle_actions(monkeypatch):
    adapter = BachAdapter(BachConfig())
    actions = []

    def fake_control(path, method="GET", payload=None):
        actions.append((path, method, payload))
        return {"ok": True, "path": path}

    monkeypatch.setattr(adapter, "_control", fake_control)

    adapter.control_create_worker({"id": "w1", "name": "Worker One", "mode": "safe"})
    assert actions[-1] == ("/api/workers", "POST", {"id": "w1", "name": "Worker One", "mode": "safe"})

    adapter.control_toggle_worker("w1", "paused")
    assert actions[-1] == ("/api/workers/toggle", "POST", {"id": "w1", "status": "paused"})

    adapter.control_stop_worker("w1")
    assert actions[-1] == ("/api/workers/stop", "POST", {"id": "w1"})

    adapter.control_run_worker("w1", prompt="Starte Audit")
    assert actions[-1] == ("/api/workers/run", "POST", {"id": "w1", "prompt": "Starte Audit"})

    adapter.control_delete_worker("w1")
    assert actions[-1] == ("/api/workers/delete", "POST", {"id": "w1"})


@pytest.mark.parametrize("auth", [None, {}, {"authenticated": False},
                                 {"service": "other", "authenticated": True},
                                 {"service": "bach-chat-control", "authenticated": "true"}])
def test_worker_capability_requires_guarded_auth_receipt(monkeypatch, auth):
    adapter = BachAdapter(BachConfig(bach_root="/missing", control_token="test-token"))
    monkeypatch.setattr(adapter, "_probe_rest", lambda: False)
    calls = []

    def control(path, method="GET", payload=None):
        calls.append((path, method))
        if path == "/api/status":
            return {"service": "bach-chat-control"}
        if path == "/api/auth/check":
            if auth is None:
                raise AdapterError("bach_control_not_found", "older backend")
            return auth
        return {}

    monkeypatch.setattr(adapter, "_control", control)
    caps = adapter.probe()
    assert Capability.CONTROL_API in caps
    assert Capability.CONTROL_WORKERS_RW not in caps
    assert all(method == "GET" for _, method in calls)


def test_worker_capability_after_authenticated_readonly_handshake(monkeypatch):
    adapter = BachAdapter(BachConfig(bach_root="/missing", control_token="test-token"))
    monkeypatch.setattr(adapter, "_probe_rest", lambda: False)
    calls = []

    def control(path, method="GET", payload=None):
        calls.append((path, method, payload))
        if path == "/api/status":
            return {"service": "bach-chat-control"}
        if path == "/api/auth/check":
            return {"service": "bach-chat-control", "authenticated": True}
        return {}

    monkeypatch.setattr(adapter, "_control", control)
    caps = adapter.probe()
    assert Capability.CONTROL_WORKERS_RW in caps
    assert Capability.CONTROL_SLOTS_RO not in caps
    assert Capability.CONTROL_ACTIVITY_RO not in caps
    assert calls[-1] == ("/api/auth/check", "GET", None)
    assert all(method == "GET" for _, method, _ in calls)


@pytest.mark.parametrize("status", [{}, [], {"service": "other-service"}])
def test_unrelated_status_endpoint_does_not_advertise_control(monkeypatch, status):
    adapter = BachAdapter(BachConfig(bach_root="/missing"))
    monkeypatch.setattr(adapter, "_probe_rest", lambda: False)
    monkeypatch.setattr(adapter, "_control", lambda *args, **kwargs: status)
    assert adapter.probe() == set()


def test_probe_shared_deadline_returns_even_when_transports_stall(monkeypatch):
    adapter = BachAdapter(BachConfig(bach_root="/missing"))
    monkeypatch.setattr(adapter, "PROBE_BUDGET_S", 0.15)
    release = threading.Event()
    finished = [threading.Event(), threading.Event()]

    def stalled(index, result):
        release.wait(5)
        finished[index].set()
        return result

    monkeypatch.setattr(adapter, "_probe_rest", lambda: stalled(0, True))
    monkeypatch.setattr(adapter, "_probe_control",
                        lambda: stalled(1, {Capability.CONTROL_WORKERS_RW}))
    try:
        started = time.monotonic()
        assert adapter.probe() == set()
        assert time.monotonic() - started < 0.8
    finally:
        release.set()
        assert all(event.wait(1) for event in finished)
    # Late completion belongs to the expired probe and cannot change health.
    assert adapter.health().status == "offline"
    assert adapter._rest_latency_ms is None
    assert adapter._control_latency_ms is None


def test_probe_request_timeouts_share_total_budget(monkeypatch):
    adapter = BachAdapter(BachConfig(bach_root="/missing", rest_timeout_s=10,
                                    control_timeout_s=10, control_token="test-token"))
    monkeypatch.setattr(adapter, "PROBE_BUDGET_S", 0.15)
    timeouts = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"service":"bach-chat-control","slots":{},"history":[]}'

    def request(req, timeout=None):
        timeouts.append(timeout)
        time.sleep(0.03)
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", request)
    monkeypatch.setattr(adapter._control_opener, "open", request)
    started = time.monotonic()
    adapter.probe()
    assert time.monotonic() - started < 0.8
    assert len(timeouts) >= 4
    # Subtraction of the large monotonic timestamp can round a deadline up.
    assert all(0 < timeout <= 0.151 for timeout in timeouts), timeouts
    assert timeouts[-1] < 0.1


@pytest.mark.parametrize("body", [b'42', b'"text"', b'{"ok":false}', b'{"error":"denied"}'])
def test_control_rejects_malformed_or_rejected_success_responses(monkeypatch, body):
    adapter = BachAdapter(BachConfig())

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return body

    monkeypatch.setattr(adapter._control_opener, "open", lambda *args, **kwargs: Response())
    with pytest.raises(AdapterError):
        adapter.control_status()


def test_control_never_forwards_token_to_redirected_origin():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    forwarded = []

    class Target(BaseHTTPRequestHandler):
        def do_GET(self):
            forwarded.append(self.headers.get("Authorization"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{}')

        def log_message(self, *args):
            pass

    target = ThreadingHTTPServer(("127.0.0.1", 0), Target)

    class Redirect(Target):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{target.server_port}/token-sink")
            self.end_headers()

    source = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    servers = [source, target]
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in servers]
    for thread in threads:
        thread.start()
    try:
        adapter = BachAdapter(BachConfig(control_url=f"http://127.0.0.1:{source.server_port}",
                                        control_token="test-device-token"))
        with pytest.raises(AdapterError) as exc:
            adapter.control_status()
        assert exc.value.kind == "bach_control_error"
        assert forwarded == []
    finally:
        for server, thread in zip(servers, threads):
            server.shutdown()
            server.server_close()
            thread.join(1)
