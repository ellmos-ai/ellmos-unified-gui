# SPDX-License-Identifier: MIT
"""P5 Rollen-Gating: Schreibaktionen nur fuer 'admin', wenn eine Host-Session
mit Rolle tatsaechlich vorliegt (ellmos-core-Mount-Betrieb) — sonst exakt das
bisherige Verhalten (kein Adapter / kein Backend / keine Session = kein
neuer Zwang). Siehe adapters/host_auth.py + panels/p5_permissions.py.

Nutzt die echte lock-master-Engine (wie test_lock_master_adapter.py); wenn
das Geschwister-Repo auf diesem System fehlt, werden diese Tests uebersprungen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from unified_gui.adapters.lock_master import LockMasterAdapter
from unified_gui.config import LockMasterConfig
from unified_gui.panels import p5_permissions

LOCK_MASTER_DIR = Path(__file__).parent.parent.parent / "lock-master"

pytestmark = pytest.mark.skipif(
    not (LOCK_MASTER_DIR / "permissions.py").is_file(),
    reason="lock-master (permissions.py) nicht vorhanden",
)


class _FakeHostAuth:
    """Test-Doppel fuer HostAuthAdapter — liefert current_user() ohne echtes
    ellmos-core im Prozess. Entspricht dem Vertrag: nie werfen."""

    def __init__(self, user: dict | None) -> None:
        self._user = user

    def current_user(self, request):  # noqa: D401 - Vertrag von HostAuthAdapter
        return self._user


@pytest.fixture
def lock_adapter(tmp_path):
    root = tmp_path / "projekt"
    root.mkdir()
    return LockMasterAdapter(LockMasterConfig(
        module_path=str(LOCK_MASTER_DIR),
        roots=[str(root)],
        watcher_url="http://127.0.0.1:1",
        timeout_s=0.2,
    ))


def _client_for(lock_adapter, auth_adapter):
    app = FastAPI()
    spec = p5_permissions.build(lock_adapter, auth_adapter)
    app.include_router(spec.router)
    return TestClient(app)


def _add_rule_payload(root):
    return {"root": str(root), "decision": "deny", "pattern": "Bash(rm:*)"}


def test_no_auth_adapter_writes_unchanged(lock_adapter):
    """Ohne auth_adapter (Standard-Fall vor 2026-08-18) bleibt jeder Schreib-
    pfad wie bisher offen — keine Regression fuer BACH-Mount/Standalone."""
    client = _client_for(lock_adapter, None)
    root = lock_adapter.roots()[0]
    resp = client.post("/api/p5/rules", json=_add_rule_payload(root))
    assert resp.status_code == 200


def test_auth_adapter_present_but_no_session_writes_unchanged(lock_adapter):
    """auth_adapter vorhanden, aber current_user() liefert None (kein Host-
    Login, z. B. ellmos-core ohne aktive Session) -> weiterhin kein Zwang."""
    client = _client_for(lock_adapter, _FakeHostAuth(None))
    root = lock_adapter.roots()[0]
    resp = client.post("/api/p5/rules", json=_add_rule_payload(root))
    assert resp.status_code == 200


def test_non_admin_role_is_forbidden_from_writing(lock_adapter):
    client = _client_for(lock_adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    root = lock_adapter.roots()[0]
    resp = client.post("/api/p5/rules", json=_add_rule_payload(root))
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]
    # Regel wurde NICHT geschrieben:
    perm = lock_adapter.rules(str(root))
    assert perm["_exists"] is False


def test_admin_role_may_write(lock_adapter):
    client = _client_for(lock_adapter, _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"}))
    root = lock_adapter.roots()[0]
    resp = client.post("/api/p5/rules", json=_add_rule_payload(root))
    assert resp.status_code == 200
    perm = lock_adapter.rules(str(root))
    assert "Bash(rm:*)" in perm["rules"]["deny"]


def test_non_admin_forbidden_from_bulk_lock(lock_adapter):
    client = _client_for(lock_adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.post("/api/p5/locks/bulk-lock")
    assert resp.status_code == 403


def test_reads_stay_open_regardless_of_role(lock_adapter):
    """Lesende Endpunkte (roots/rules/evaluate) sind absichtlich NICHT
    gegated — nur Schreibpfade aendern die Regeln."""
    client = _client_for(lock_adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    root = lock_adapter.roots()[0]
    assert client.get("/api/p5/roots").status_code == 200
    assert client.get("/api/p5/rules", params={"root": str(root)}).status_code == 200
