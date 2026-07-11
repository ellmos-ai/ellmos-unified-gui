# SPDX-License-Identifier: MIT
"""Scanner-Task-Adapter: read-only-Lesen + P7-Aggregation mit Provenienz."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from starlette.testclient import TestClient

from unified_gui import create_app
from unified_gui.adapters.scanner_tasks import ScannerTasksAdapter
from unified_gui.capabilities import Capability
from unified_gui.config import ScannerTasksConfig


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE rinnsal_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        description TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'open',
        priority TEXT NOT NULL DEFAULT 'medium', agent_id TEXT NOT NULL DEFAULT 'default',
        tags TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        done_at TEXT)""")
    conn.executemany(
        "INSERT INTO rinnsal_tasks (title, status, priority, agent_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, '2026-07-11', '2026-07-11')",
        [("Kritischer Fix", "open", "critical", "default"),
         ("Doku nachziehen", "open", "low", "sonnet-1"),
         ("Erledigtes", "done", "medium", "default")],
    )
    conn.commit()
    conn.close()


def test_scanner_read_and_priority_order(tmp_path):
    db = tmp_path / "scanner_tasks.db"
    _make_db(db)
    adapter = ScannerTasksAdapter(ScannerTasksConfig(db_path=str(db)))

    caps = adapter.probe()
    assert Capability.TASKS_RO in caps
    assert Capability.TASKS_ASSIGN not in caps  # kein tool_path konfiguriert

    tasks = adapter.tasks()
    assert tasks[0]["title"] == "Kritischer Fix"  # critical zuerst
    assert tasks[0]["provenance"] == "scanner"
    doku = next(t for t in tasks if t["title"] == "Doku nachziehen")
    assert doku["assigned_to"] == "sonnet-1"

    open_only = adapter.tasks(status="open")
    assert len(open_only) == 2


def test_p7_aggregation_with_scanner_only(tmp_path):
    db = tmp_path / "scanner_tasks.db"
    _make_db(db)
    app = create_app({
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": "/nonexistent"},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": str(db)},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
    })
    client = TestClient(app)

    assert "p7" in client.get("/api/status").json()["panels"]
    data = client.get("/api/p7/tasks").json()
    assert len(data["tasks"]) == 3
    assert all(t["provenance"] == "scanner" for t in data["tasks"])
    bach_source = next(s for s in data["sources"] if s["name"] == "bach")
    assert bach_source["available"] is False  # Provenienz-Report statt Fehler

    # Zuweisen ohne Tool -> fachlicher Fehler, kein Crash
    resp = client.post("/api/p7/assign", json={"provenance": "scanner", "id": 1, "target": "opus-1"})
    assert resp.status_code == 409
