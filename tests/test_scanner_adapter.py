# SPDX-License-Identifier: MIT
"""Scanner-Task-Adapter: read-only-Lesen + P7-Aggregation mit Provenienz.

Schwerpunkt seit TASKPLAN 0.3: WER ist der Bearbeiter? `agent_id` trug frueher
drei Bedeutungen (Anleger, Bearbeiter, Rolle); ein naiver Fallback zeigt deshalb
den Anleger als Bearbeiter an. Beide Schemata werden getestet — der Adapter liest
strikt read-only und kann eine alte DB nie selbst migrieren.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from starlette.testclient import TestClient

from unified_gui import create_app
from unified_gui.adapters.scanner_tasks import ScannerTasksAdapter
from unified_gui.capabilities import Capability
from unified_gui.config import ScannerTasksConfig

_LEGACY_SCHEMA = """CREATE TABLE rinnsal_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
    description TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium', agent_id TEXT NOT NULL DEFAULT 'default',
    tags TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    done_at TEXT)"""

# TASKPLAN 0.3: created_by (Anleger, unveraenderlich) und assigned_to (Bearbeiter)
# sind getrennt; agent_id wird beim Zuweisen nicht mehr ueberschrieben.
_V03_SCHEMA = _LEGACY_SCHEMA.rstrip(")") + """,
    project_path TEXT DEFAULT '', root_id TEXT DEFAULT '', effort TEXT DEFAULT '',
    scope TEXT DEFAULT 'local', source TEXT DEFAULT '', created_by TEXT DEFAULT '',
    assigned_to TEXT DEFAULT '', delegation_status TEXT DEFAULT '')"""


def _make_legacy_db(path: Path) -> None:
    """DB im Ur-Schema — ein System, auf dem TASKPLAN 0.3 noch nicht lief."""
    conn = sqlite3.connect(path)
    conn.execute(_LEGACY_SCHEMA)
    conn.executemany(
        "INSERT INTO rinnsal_tasks (title, status, priority, agent_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, '2026-07-11', '2026-07-11')",
        [("Kritischer Fix", "open", "critical", "default"),
         ("Doku nachziehen", "open", "low", "sonnet-1"),
         ("Erledigtes", "done", "medium", "default")],
    )
    conn.commit()
    conn.close()


def _make_db(path: Path) -> None:
    """DB im v0.3-Schema — deckt alle Faelle ab, die _assignee unterscheiden muss."""
    conn = sqlite3.connect(path)
    conn.execute(_V03_SCHEMA)
    conn.executemany(
        "INSERT INTO rinnsal_tasks (title, status, priority, agent_id, created_by, "
        "assigned_to, effort, scope, project_path, root_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-07-11', '2026-07-11')",
        [
            # zugewiesen: assigned_to ist die Wahrheit, agent_id bleibt der Anleger
            ("Kritischer Fix", "open", "critical", "scanner", "scanner", "opus-1",
             "medium", "local", "C:/Projekte/alpha", ".AI"),
            # Altbestand: agent_id trug den echten Bearbeiter (alter Wrapper)
            ("Doku nachziehen", "open", "low", "sonnet-1", "", "",
             "easy", "local", "C:/Projekte/beta", ".AI"),
            # nicht zugewiesen, uneingestuft: agent_id = Anleger, created_by leer
            ("Uneingestuft", "open", "medium", "scanner", "", "",
             "", "local", "C:/Projekte/gamma", ".SOFTWARE"),
            ("Erledigtes", "done", "medium", "default", "", "",
             "easy", "central", "", ""),
        ],
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

    open_only = adapter.tasks(status="open")
    assert len(open_only) == 3


def test_assignee_is_the_worker_never_the_creator(tmp_path):
    """Der Kern von TASKPLAN 0.3: angezeigt wird der Bearbeiter, nie der Anleger.

    Ein `assigned_to or agent_id`-Fallback wuerde hier "scanner" als Bearbeiter
    zeigen — im echten Bestand bei 25 von 44 Tasks.
    """
    db = tmp_path / "scanner_tasks.db"
    _make_db(db)
    tasks = {t["title"]: t for t in ScannerTasksAdapter(
        ScannerTasksConfig(db_path=str(db))).tasks()}

    # assigned_to gewinnt — obwohl agent_id "scanner" (der Anleger) traegt
    assert tasks["Kritischer Fix"]["assigned_to"] == "opus-1"
    assert tasks["Kritischer Fix"]["created_by"] == "scanner"
    # Altbestand ohne assigned_to: agent_id war der echte Bearbeiter
    assert tasks["Doku nachziehen"]["assigned_to"] == "sonnet-1"
    # Anleger-Sentinel: 'scanner' ist NIE ein Bearbeiter, auch bei leerem created_by
    assert tasks["Uneingestuft"]["assigned_to"] == ""
    # Platzhalter 'default' ebenso wenig
    assert tasks["Erledigtes"]["assigned_to"] == ""


def test_effort_scope_and_project_are_exposed(tmp_path):
    """effort/scope/project_path entscheiden, ob ein Loop die Aufgabe anfasst."""
    db = tmp_path / "scanner_tasks.db"
    _make_db(db)
    tasks = {t["title"]: t for t in ScannerTasksAdapter(
        ScannerTasksConfig(db_path=str(db))).tasks()}

    assert tasks["Kritischer Fix"]["effort"] == "medium"
    assert tasks["Kritischer Fix"]["scope"] == "local"
    assert tasks["Kritischer Fix"]["project_path"] == "C:/Projekte/alpha"
    assert tasks["Kritischer Fix"]["root_id"] == ".AI"
    # leeres effort = uneingestuft: die GUI markiert das sichtbar
    assert tasks["Uneingestuft"]["effort"] == ""


def test_legacy_schema_degrades_instead_of_crashing(tmp_path):
    """Alte DB (ohne die v0.3-Spalten): weniger anzeigen, aber nicht brechen.

    Der Adapter oeffnet mode=ro und kann nie selbst migrieren — er haengt davon
    ab, dass ein anderes System die DB migriert hat. Ein harter SELECT auf die
    neuen Spalten wuerde das Panel mit "no such column" stilllegen.
    """
    db = tmp_path / "scanner_tasks.db"
    _make_legacy_db(db)
    tasks = {t["title"]: t for t in ScannerTasksAdapter(
        ScannerTasksConfig(db_path=str(db))).tasks()}

    assert len(tasks) == 3  # kein Crash
    assert tasks["Doku nachziehen"]["assigned_to"] == "sonnet-1"  # Fallback greift
    assert tasks["Kritischer Fix"]["assigned_to"] == ""           # 'default' bleibt leer
    assert tasks["Kritischer Fix"]["effort"] == ""                # Spalte fehlt -> leer
    assert tasks["Kritischer Fix"]["scope"] == ""


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
        "ellmos_chat": {"module_path": "/nonexistent"},
    })
    client = TestClient(app)

    assert "p7" in client.get("/api/status").json()["panels"]
    data = client.get("/api/p7/tasks").json()
    assert len(data["tasks"]) == 4
    assert all(t["provenance"] == "scanner" for t in data["tasks"])
    bach_source = next(s for s in data["sources"] if s["name"] == "bach")
    assert bach_source["available"] is False  # Provenienz-Report statt Fehler

    # Zuweisen ohne Tool -> fachlicher Fehler, kein Crash
    resp = client.post("/api/p7/assign", json={"provenance": "scanner", "id": 1, "target": "opus-1"})
    assert resp.status_code == 409

    # Die Seite selbst laedt (Jinja-Template uebersetzt). Das JS darin — taskChips(),
    # der "uneingestuft"-Chip — laeuft hier NICHT: dafuer braeuchte es einen Browser.
    page = client.get("/p7")
    assert page.status_code == 200
    assert "taskChips" in page.text


def test_p7_task_values_are_never_interpolated_as_html():
    """Backend-Taskwerte muessen als DOM-Text statt als HTML gerendert werden.

    project_path, title und weitere Taskfelder kommen aus externen Backends. Ein
    `innerHTML`-Renderer oder Inline-Handler macht ein Anführungszeichen in
    project_path zu einem Attribut-Injection-Sink.
    """
    template = (Path(__file__).parent.parent / "src" / "unified_gui" / "web"
                / "templates" / "p7_tasks.html").read_text(encoding="utf-8")

    assert 'document.getElementById("task-list").innerHTML' not in template
    assert "insertAdjacentHTML" not in template
    assert "onclick=" not in template
    assert "replaceChildren(" in template
    assert "addEventListener(" in template
