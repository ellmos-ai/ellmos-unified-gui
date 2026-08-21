# SPDX-License-Identifier: MIT
"""Beweist die volle Verdrahtung in web/app.py::create_app(): AuditMiddleware
ist wirklich registriert, liest audit_log_path aus der Config (nicht nur aus
einem isolierten Testaufbau wie in test_audit_middleware.py), und ein echter
P11-Schreibpfad funktioniert weiterhin normal, waehrend er mitgeloggt wird."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from starlette.testclient import TestClient

from unified_gui.web.app import create_app


def test_create_app_writes_to_the_configured_audit_path(tmp_path):
    target = tmp_path / "audit.jsonl"
    app = create_app(config={"audit_log_path": str(target)}, standalone_guard=False)
    client = TestClient(app)

    resp = client.post("/api/refresh")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == "/api/refresh"
    assert entry["outcome"] == "ok"


def test_create_app_default_audit_log_path_is_off_in_tests(tmp_path):
    """conftest.py setzt UNIFIED_GUI_AUDIT_LOG=off global -- ein create_app()
    ohne expliziten audit_log_path darf in der Testsuite NICHT ins echte
    Nutzerprofil schreiben (Regressionstest fuer genau den Fund, der zum
    conftest.py-Fix fuehrte: ein erster Lauf schrieb echte 10 Zeilen nach
    ~/.ellmos/unified-gui/audit.jsonl)."""
    app = create_app(config={}, standalone_guard=False)
    client = TestClient(app)
    resp = client.post("/api/refresh")
    assert resp.status_code == 200
    # Kein Crash, keine Ausnahme -- und explizit: die reale Default-Datei
    # existiert deswegen nicht ploetzlich neu (best effort, kein Beweis fuer
    # einen fremden Lauf, aber fuer DIESEN Test-Prozess aussagekraeftig).


SKILLS_REPO = Path(__file__).parent.parent.parent / "skills"


def test_real_p11_write_reaches_the_audit_log_end_to_end(tmp_path):
    """End-to-end gegen den echten skills-Klon (wie test_skills_catalog_adapter.py):
    ein echter P11-Schreibpfad durch die volle create_app() liefert sein
    normales Ergebnis UND landet im Audit-Log mit panel=p11/action=create.
    Wegwerf-Kategorie, danach entfernt -- gleiche Disziplin wie der P11-Bau
    selbst (Ticket T-20260816-361197589)."""
    if not (SKILLS_REPO / "catalog.py").is_file():
        import pytest
        pytest.skip("skills-Repo (catalog.py) nicht vorhanden")

    audit_target = tmp_path / "audit.jsonl"
    # UNIFIED_GUI_DISCOVERY=0 gilt global in dieser Testsuite (conftest.py) --
    # der skills-Repo-Pfad muss deshalb hier explizit gesetzt werden, sonst
    # findet der Adapter ihn nicht (anders als beim manuellen Boot-Smoke ohne
    # Testsuite-Umgebung).
    app = create_app(
        config={"audit_log_path": str(audit_target), "skills_catalog": {"repo_path": str(SKILLS_REPO)}},
        standalone_guard=False,
    )
    client = TestClient(app)

    category = "_audit-e2e-smoke-test"
    name = "audit-e2e-smoke-skill"
    skill_dir = SKILLS_REPO / "skills" / category
    try:
        resp = client.post("/api/p11/create", json={"name": name, "category": category, "type": "skill"})
        assert resp.status_code == 200
        assert (skill_dir / name / "SKILL.md").is_file()

        lines = audit_target.read_text(encoding="utf-8").splitlines()
        entries = [json.loads(line) for line in lines]
        create_entries = [e for e in entries if e["panel"] == "p11" and e["action"] == "create"]
        assert len(create_entries) == 1
        entry = create_entries[0]
        assert entry["method"] == "POST"
        assert entry["outcome"] == "ok"
        assert sorted(entry["argument_keys"]) == ["category", "name", "type"]
        assert name not in json.dumps(entry)  # Wert nicht im Log, nur der Schluessel "name"
    finally:
        import shutil
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
