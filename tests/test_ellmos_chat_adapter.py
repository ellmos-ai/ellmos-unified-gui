# SPDX-License-Identifier: MIT
"""EllmosChatAdapter: Pflicht-Degradierung wenn ellmos-chat (Staging-Modul,
kein pip-Paket) nicht am konfigurierten module_path liegt -- nie eine
Ausnahme, nie eine falsch-positive Capability (ADAPTER-CONTRACT.md §1/§5).

Wheelhouse M1, T-20260825-835413946."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from starlette.testclient import TestClient

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.ellmos_chat import EllmosChatAdapter
from unified_gui.capabilities import Capability
from unified_gui.config import EllmosChatConfig

# ellmos-chat lebt heute nur als OneDrive-Staging-Modul (Fixpfad in
# config.DISCOVERY_DEFAULTS) -- auf Systemen ohne diesen Ordner (z. B. CI-
# Runner) ist der positive Pfad nicht pruefbar; er wird dort uebersprungen,
# der negative Degradierungspfad (unten) bleibt ueberall pruefbar.
_REAL_MODULE_PATH = "~/OneDrive/.TOPICS/.AI/.MODULES/.RUNTIME/ellmos-chat"


def _real_module_present() -> bool:
    marker = Path(_REAL_MODULE_PATH).expanduser() / "src" / "ellmos_chat" / "__init__.py"
    return marker.is_file()


@pytest.fixture
def missing_adapter():
    return EllmosChatAdapter(EllmosChatConfig(module_path="/nonexistent"))


def test_probe_empty_without_module(missing_adapter):
    assert missing_adapter.probe() == set()


def test_health_offline_without_module(missing_adapter):
    health = missing_adapter.health()
    assert health.status == "offline"


def test_ask_raises_adaptererror_when_module_missing(missing_adapter):
    with pytest.raises(AdapterError):
        asyncio.run(missing_adapter.ask("Hallo?"))


def test_ask_empty_text_raises_before_touching_backend(missing_adapter):
    """Leerer Text scheitert an der Eingabepruefung -- unabhaengig davon, ob
    das Modul/Backend ueberhaupt erreichbar waere (kein Netzwerk-/Prozess-
    Aufruf fuer eine ohnehin ungueltige Eingabe)."""
    with pytest.raises(AdapterError):
        asyncio.run(missing_adapter.ask("   "))


def test_probe_never_raises_on_garbage_module_path():
    adapter = EllmosChatAdapter(EllmosChatConfig(module_path="::not\a/valid<>path::"))
    assert adapter.probe() == set()


def test_capability_is_additive_and_named():
    assert Capability.CHAT_RUNTIME.value == "chat.runtime"


def test_registered_in_create_app_status_without_crashing():
    """Der Adapter wird in create_app() registriert; die Status-API muss
    unabhaengig davon funktionieren, ob ellmos-chat am konfigurierten
    module_path liegt."""
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
        "ellmos_chat": {"module_path": "/nonexistent"},
    })
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert "p13" not in resp.json()["panels"]


def _app_without_ellmos_chat():
    from unified_gui import create_app

    return create_app({
        "lock_master": {"module_path": "/nonexistent", "roots": [], "roots_file": None,
                        "watcher_url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "ticket_master": {"tickets_root": "/nonexistent"},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
        "ellmos_chat": {"module_path": "/nonexistent"},
    })


def test_p13_route_redirects_when_backend_missing():
    """Pflicht-Testklasse (README/Ticket-Scope): Backend fehlt -> Panel
    unsichtbar, App laeuft trotzdem (kein Crash) -- P13 im Speziellen."""
    client = TestClient(_app_without_ellmos_chat())
    resp = client.get("/p13", follow_redirects=False)
    assert resp.status_code == 302


def test_p13_ask_degrades_not_500_when_backend_missing():
    client = TestClient(_app_without_ellmos_chat())
    resp = client.post("/api/p13/ask", json={"text": "Hallo?"})
    assert resp.status_code == 409  # AdapterError -> fachlicher Fehler, kein Crash


@pytest.mark.skipif(not _real_module_present(),
                    reason="ellmos-chat-Staging-Modul liegt auf diesem System nicht unter "
                           "module_path -- positiver Pfad nicht pruefbar (z. B. CI-Runner)")
def test_probe_available_with_real_staging_module():
    """Verifiziert, dass provides=[chat.runtime] im Manifest von ellmos-chat
    real belegt ist (echte backend.py/runtime.py), nicht nur behauptet --
    genau die Bedingung aus dem Ticket ('NUR wenn die Faehigkeit real belegt
    ist')."""
    adapter = EllmosChatAdapter(EllmosChatConfig(module_path=_REAL_MODULE_PATH))
    caps = adapter.probe()
    assert caps == {Capability.CHAT_RUNTIME}
    health = adapter.health()
    assert health.status == "ok"
