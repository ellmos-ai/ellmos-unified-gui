# SPDX-License-Identifier: MIT
"""Pflicht-Tests: Backend fehlt => Panel unsichtbar, App laeuft trotzdem (kein Crash)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from starlette.testclient import TestClient

from unified_gui import create_app


def _app_without_backends():
    return create_app({
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": "/nonexistent"},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
    })


def test_index_ok_without_backends():
    client = TestClient(_app_without_backends())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Kein Panel aktiv" in resp.text


def test_status_reports_no_panels():
    client = TestClient(_app_without_backends())
    data = client.get("/api/status").json()
    assert data["panels"] == []
    assert data["available"] == []


def test_panel_page_redirects_when_backend_missing():
    client = TestClient(_app_without_backends())
    resp = client.get("/p8", follow_redirects=False)
    assert resp.status_code == 302


def test_panel_api_degrades_not_500(tmp_path):
    client = TestClient(_app_without_backends())
    resp = client.post("/api/p8/intake", json={"title": "x"})
    assert resp.status_code == 409  # AdapterError -> fachlicher Fehler, kein Crash


def test_refresh_picks_up_new_backend(tmp_path):
    app = create_app({
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": str(tmp_path / "missing")},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
    })
    client = TestClient(app)
    assert client.get("/api/status").json()["panels"] == []

    (tmp_path / "missing").mkdir()
    data = client.post("/api/refresh").json()
    assert "p8" in data["panels"]
    assert client.get("/p8", follow_redirects=False).status_code == 200
