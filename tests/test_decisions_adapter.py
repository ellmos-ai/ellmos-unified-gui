# SPDX-License-Identifier: MIT
"""decisions-Adapter (P10, read-only): Schema-Vertrag, Filter/Sortierung,
Degradierung bei fehlender/kaputter Index-Datei, Read-only-Nachweis des Panels."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from starlette.testclient import TestClient

from unified_gui import create_app
from unified_gui.adapters.decisions import DecisionsAdapter
from unified_gui.capabilities import Capability
from unified_gui.config import DecisionsConfig
from unified_gui.panels import p10_decisions

SCHEMA = "decisions.index/1"

# Konfig-Grundgerüst fuer create_app()-Tests: alle anderen Backends bewusst
# abwesend, damit einzig der decisions-Adapter das Bild bestimmt.
_OTHER_BACKENDS_OFF = {
    "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                    "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
    "ticket_master": {"tickets_root": "/nonexistent"},
    "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
    "scanner_tasks": {"db_path": None, "tool_path": None},
    "clutch": {"repo_path": None},
    "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
    "controlcenter": {"repo_path": None},
}


def _entry(key, status_class, scope="global", date="2026-07-01", **extra):
    base = {
        "key": key, "id": key.split("#")[0], "collision_suffix": None,
        "date": date, "title": f"Titel {key}", "question": f"Frage {key}?",
        "status_class": status_class, "status_raw": status_class,
        "scope": scope, "scope_explicit": False,
        "decision_field_raw": "", "options_excerpt": "A oder B",
        "recommendation_excerpt": "A", "source_excerpt": "",
        "is_alias": False, "alias_of": None, "domain": "active",
        "source_file": "TO-DECIDE-USER.txt",
        "source_path": "C:\\x\\TO-DECIDE-USER.txt",
        "source_line": 10, "chain_part": 1,
    }
    base.update(extra)
    return base


def _write_index(path, entries, collisions=None):
    payload = {
        "schema": SCHEMA, "generated_at": "2026-08-01T12:00:00", "generator": "test",
        "root": str(path.parent), "files": [],
        "counts": {
            "total": len(entries), "active_chain": len(entries),
            "by_status_class": {}, "by_scope": {},
            "id_collisions": len(collisions or []), "ids_in_active_and_history": 0,
        },
        "collisions": collisions or [],
        "entries": entries,
    }
    for e in entries:
        payload["counts"]["by_status_class"][e["status_class"]] = \
            payload["counts"]["by_status_class"].get(e["status_class"], 0) + 1
        payload["counts"]["by_scope"][e["scope"]] = \
            payload["counts"]["by_scope"].get(e["scope"], 0) + 1
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


@pytest.fixture
def index_path(tmp_path):
    return tmp_path / "decisions.index.json"


@pytest.fixture
def sample_entries():
    return [
        _entry("D-20260801-001", "OFFEN", scope="global", date="2026-08-01"),
        _entry("D-20260731-002", "OFFEN", scope="project-x", date="2026-07-31"),
        _entry("D-20260701-003", "ENTSCHIEDEN_UMSETZUNG_OFFEN", scope="global", date="2026-07-01"),
        _entry("D-20260601-004", "DONE", scope="global", date="2026-06-01"),
        _entry("D-20260501-005", "ARCHIVIERT", scope="global", date="2026-05-01"),
    ]


@pytest.fixture
def sample_collisions():
    return [{
        "id": "D-20260731-009", "count": 2,
        "occurrences": [
            {"key": "D-20260731-009#a", "title": "A", "source_file": "x.txt", "line": 1},
            {"key": "D-20260731-009#b", "title": "B", "source_file": "x.txt", "line": 2},
        ],
    }]


@pytest.fixture
def adapter(index_path, sample_entries, sample_collisions):
    _write_index(index_path, sample_entries, sample_collisions)
    return DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))


# ------------------------------------------------------------------
# probe() / health() — inkl. Degradierung
# ------------------------------------------------------------------
def test_probe_with_valid_index(adapter):
    assert adapter.probe() == {Capability.DECISIONS_RO}
    assert adapter.health().status == "ok"


def test_probe_no_path_configured():
    adapter = DecisionsAdapter(DecisionsConfig())
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_probe_missing_file(tmp_path):
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(tmp_path / "nope.json")))
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_probe_corrupt_json(index_path):
    index_path.write_text("{not valid json", encoding="utf-8")
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    assert adapter.probe() == set()
    assert adapter.health().status == "degraded"


def test_probe_wrong_schema(index_path):
    index_path.write_text(json.dumps({"schema": "other/1", "entries": []}), encoding="utf-8")
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    assert adapter.probe() == set()
    assert adapter.health().status == "degraded"


def test_probe_missing_entries_key(index_path):
    index_path.write_text(json.dumps({"schema": SCHEMA}), encoding="utf-8")
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    assert adapter.probe() == set()
    assert adapter.health().status == "degraded"


def test_probe_path_is_directory_not_file(tmp_path):
    # Verzeichnis statt Datei -> is_file() False -> gilt wie "fehlt", kein Crash
    d = tmp_path / "decisions.index.json"
    d.mkdir()
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(d)))
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_probe_never_raises_even_on_unexpected_content(index_path):
    index_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    assert adapter.probe() == set()  # nie werfen -- Vertrag aus base.py


# ------------------------------------------------------------------
# entries(): Sortierung (offen zuerst), Scope-/Status-Filter
# ------------------------------------------------------------------
def test_entries_default_hides_done_and_archived_offen_first(adapter):
    rows = adapter.entries()
    classes = [r["status_class"] for r in rows]
    assert "DONE" not in classes
    assert "ARCHIVIERT" not in classes
    assert classes[:2] == ["OFFEN", "OFFEN"]
    assert classes[2] == "ENTSCHIEDEN_UMSETZUNG_OFFEN"
    assert len(rows) == 3


def test_entries_scope_filter(adapter):
    rows = adapter.entries(scope="project-x")
    assert [r["id"] for r in rows] == ["D-20260731-002"]


def test_entries_status_class_filter_reveals_done(adapter):
    rows = adapter.entries(status_class="DONE")
    assert [r["id"] for r in rows] == ["D-20260601-004"]


def test_entries_status_class_filter_reveals_archiviert(adapter):
    rows = adapter.entries(status_class="ARCHIVIERT")
    assert [r["id"] for r in rows] == ["D-20260501-005"]


def test_entries_combined_scope_and_status_filter(adapter):
    rows = adapter.entries(scope="global", status_class="OFFEN")
    assert [r["id"] for r in rows] == ["D-20260801-001"]


def test_entries_unknown_scope_returns_empty(adapter):
    assert adapter.entries(scope="does-not-exist") == []


# ------------------------------------------------------------------
# summary() / collisions() / scopes()
# ------------------------------------------------------------------
def test_summary_counts_and_metadata(adapter):
    summary = adapter.summary()
    assert summary["counts"]["total"] == 5
    assert summary["counts"]["by_status_class"]["OFFEN"] == 2
    assert summary["generated_at"] == "2026-08-01T12:00:00"
    assert "entries" not in summary  # Kopf ohne entries[]


def test_collisions_exposed(adapter):
    collisions = adapter.collisions()
    assert len(collisions) == 1
    assert collisions[0]["id"] == "D-20260731-009"
    assert collisions[0]["count"] == 2


def test_scopes_lists_distinct_scopes(adapter):
    assert set(adapter.scopes()) == {"global", "project-x"}


# ------------------------------------------------------------------
# mtime-Cache: Datei aendert sich -> neu gelesen
# ------------------------------------------------------------------
def test_cache_refreshes_on_mtime_change(index_path, sample_entries):
    _write_index(index_path, sample_entries)
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    assert len(adapter.entries()) == 3  # 2x OFFEN + 1x ENTSCHIEDEN..., DONE/ARCHIVIERT versteckt

    new_entries = sample_entries + [_entry("D-20260801-999", "OFFEN", scope="global", date="2026-08-01")]
    _write_index(index_path, new_entries)
    # mtime robust vorwaerts setzen (manche Dateisysteme haben nur Sekundenaufloesung)
    bumped = index_path.stat().st_mtime + 5
    os.utime(index_path, (bumped, bumped))

    assert len(adapter.entries()) == 4


def test_cache_survives_unchanged_mtime(index_path, sample_entries):
    """Zweiter Aufruf ohne Dateiaenderung liefert dasselbe (gecachte) Ergebnis."""
    _write_index(index_path, sample_entries)
    adapter = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))
    first = adapter.entries()
    second = adapter.entries()
    assert first == second


# ------------------------------------------------------------------
# Panel: Read-only-Nachweis (P10-Router bietet ausschliesslich GET-Routen)
# ------------------------------------------------------------------
def test_panel_router_is_get_only(adapter):
    spec = p10_decisions.build(adapter)
    assert spec.id == "p10"
    assert spec.required == {Capability.DECISIONS_RO}
    assert spec.router is not None
    write_verbs = {"POST", "PUT", "PATCH", "DELETE"}
    for route in spec.router.routes:
        methods = getattr(route, "methods", set()) or set()
        assert not (methods & write_verbs), f"{route.path} erlaubt Schreib-Verben: {methods}"
        assert methods <= {"GET", "HEAD"}


# ------------------------------------------------------------------
# Integration ueber create_app(): Sichtbarkeit, Degradierung, kein Crash
# ------------------------------------------------------------------
def test_app_shows_p10_when_index_valid(index_path, sample_entries, sample_collisions):
    _write_index(index_path, sample_entries, sample_collisions)
    app = create_app({**_OTHER_BACKENDS_OFF, "decisions": {"index_path": str(index_path)}})
    client = TestClient(app)

    assert client.get("/api/status").json()["panels"] == ["p10"]
    assert client.get("/p10").status_code == 200

    entries_resp = client.get("/api/p10/entries").json()
    assert entries_resp["count"] == 3
    assert entries_resp["entries"][0]["status_class"] == "OFFEN"

    summary_resp = client.get("/api/p10/summary").json()
    assert summary_resp["counts"]["total"] == 5
    assert len(summary_resp["collisions"]) == 1

    filtered = client.get("/api/p10/entries", params={"status_class": "DONE"}).json()
    assert filtered["count"] == 1


def test_app_p10_endpoints_reject_write_verbs(index_path, sample_entries):
    _write_index(index_path, sample_entries)
    app = create_app({**_OTHER_BACKENDS_OFF, "decisions": {"index_path": str(index_path)}})
    client = TestClient(app)

    assert client.post("/api/p10/entries").status_code == 405
    assert client.delete("/api/p10/summary").status_code == 405


def test_app_degrades_when_index_missing(tmp_path):
    app = create_app({**_OTHER_BACKENDS_OFF,
                      "decisions": {"index_path": str(tmp_path / "missing.json")}})
    client = TestClient(app)

    assert client.get("/api/status").json()["panels"] == []
    resp = client.get("/p10", follow_redirects=False)
    assert resp.status_code == 302  # zurueck zur Uebersicht statt Fehlerseite


def test_app_degrades_when_index_corrupt(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not json", encoding="utf-8")
    app = create_app({**_OTHER_BACKENDS_OFF, "decisions": {"index_path": str(broken)}})
    client = TestClient(app)

    assert client.get("/api/status").json()["panels"] == []  # kein Crash, nur unsichtbar
    assert client.get("/", follow_redirects=False).status_code == 200


def test_app_without_decisions_config_has_no_p10(tmp_path):
    """Kein 'decisions'-Key in der Config -> Adapter ohne index_path -> Panel fehlt."""
    app = create_app(dict(_OTHER_BACKENDS_OFF))
    client = TestClient(app)
    assert "p10" not in client.get("/api/status").json()["panels"]
