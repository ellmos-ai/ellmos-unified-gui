# SPDX-License-Identifier: MIT
"""HostAuthAdapter: degradiert sauber, wenn ellmos-core nicht im Prozess ist
(Standard-Fall in dieser Test-Umgebung, im BACH-Mount und im Standalone-
Betrieb) -- nie eine Ausnahme, nie eine falsch-positive Capability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from starlette.testclient import TestClient

from unified_gui.adapters.host_auth import HostAuthAdapter
from unified_gui.capabilities import Capability


@pytest.fixture
def adapter():
    return HostAuthAdapter()


def _ellmos_core_importable() -> bool:
    try:
        import ellmos_core  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(_ellmos_core_importable(),
                    reason="ellmos-core ist in dieser Umgebung installiert -- Degradierungspfad nicht pruefbar")
def test_probe_empty_without_ellmos_core(adapter):
    assert adapter.probe() == set()


@pytest.mark.skipif(_ellmos_core_importable(),
                    reason="ellmos-core ist in dieser Umgebung installiert -- Degradierungspfad nicht pruefbar")
def test_health_offline_without_ellmos_core(adapter):
    health = adapter.health()
    assert health.status == "offline"


@pytest.mark.skipif(_ellmos_core_importable(),
                    reason="ellmos-core ist in dieser Umgebung installiert -- Degradierungspfad nicht pruefbar")
def test_current_user_none_without_ellmos_core(adapter):
    class _FakeRequest:
        pass

    assert adapter.current_user(_FakeRequest()) is None


def test_never_raises_on_malformed_request(adapter):
    """current_user() darf nie werfen, egal was uebergeben wird
    (ADAPTER-CONTRACT.md §5)."""
    assert adapter.current_user(None) is None
    assert adapter.current_user(object()) is None


def test_capability_is_additive_and_named():
    assert Capability.AUTH_ROLE.value == "auth.role"


def test_registered_in_create_app_status_without_crashing():
    """Der Adapter wird in create_app() registriert; die Status-API muss
    unabhaengig davon funktionieren, ob ellmos-core installiert ist."""
    from unified_gui import create_app

    app = create_app({
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": "/nonexistent"},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
    })
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
