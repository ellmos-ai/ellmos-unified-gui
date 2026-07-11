# SPDX-License-Identifier: MIT
"""Mount-Betrieb: Einbettung als Sub-App, Links muessen prefix-sicher sein."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI
from starlette.testclient import TestClient

import unified_gui


def _mounted_client(tmp_path):
    (tmp_path / "TICKETS").mkdir()
    host = FastAPI()
    unified_gui.mount(host, prefix="/control", config={
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": str(tmp_path / "TICKETS"), "config_dir": None},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
    })
    return TestClient(host)


def test_mounted_index_and_status(tmp_path):
    client = _mounted_client(tmp_path)
    assert client.get("/control/").status_code == 200
    assert client.get("/control/api/status").json()["panels"] == ["p8"]


def test_mounted_links_are_prefix_safe(tmp_path):
    client = _mounted_client(tmp_path)
    html = client.get("/control/").text
    assert '/control/static/app.css' in html
    assert 'href="/control/p8"' in html


def test_mounted_panel_api(tmp_path):
    client = _mounted_client(tmp_path)
    data = client.post("/control/api/p8/intake",
                       json={"title": "Mount-Test"}).json()
    assert data["id"].startswith("T-")
    queues = client.get("/control/api/p8/queues").json()
    assert len(queues["OPEN"]) == 1


def test_host_root_untouched(tmp_path):
    client = _mounted_client(tmp_path)
    # Host selbst hat keine eigene Route -> 404, aber nicht von der Sub-App gekapert
    assert client.get("/").status_code == 404
