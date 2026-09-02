# SPDX-License-Identifier: MIT
"""Cloud-/Multi-System-Konfiguration: Expansion, Kaskade, Host-Override, Discovery."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.config import (
    SCANNER_DB_FALLBACK,
    UnifiedGuiConfig,
    _expand,
    hostname,
    resolve_module_path,
    scanner_db_default,
)


def test_expand_user_and_env(monkeypatch):
    monkeypatch.setenv("UG_TESTVAR", "wert123")
    assert _expand("~/x").startswith(str(Path.home()))
    assert "wert123" in _expand("$UG_TESTVAR/pfad")
    if os.name == "nt":
        assert "wert123" in _expand("%UG_TESTVAR%/pfad")
    assert _expand(None) is None


def test_config_paths_are_expanded(tmp_path, monkeypatch):
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps({
        "ticket_master": {"tickets_root": "~/TICKETS-XYZ"},
        "bach": {"bach_root": "$UG_ROOT/BACH"},
    }), encoding="utf-8")
    monkeypatch.setenv("UG_ROOT", str(tmp_path))
    monkeypatch.setenv("UNIFIED_GUI_DISCOVERY", "0")
    cfg = UnifiedGuiConfig.load(config_file=cfg_file)
    assert "~" not in cfg.ticket_master.tickets_root
    assert cfg.ticket_master.tickets_root.startswith(str(Path.home()))
    assert "$UG_ROOT" not in cfg.bach.bach_root
    assert str(tmp_path) in cfg.bach.bach_root


def test_host_config_wins_over_base(tmp_path, monkeypatch):
    # Kaskade simulieren: UNIFIED_GUI_CONFIG loeschen, HOME/Shared umleiten
    monkeypatch.delenv("UNIFIED_GUI_CONFIG", raising=False)
    monkeypatch.setenv("UNIFIED_GUI_DISCOVERY", "0")
    user_dir = tmp_path / ".unified_gui"
    user_dir.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr("unified_gui.config.SHARED_CONFIG_DIR", str(tmp_path / "shared"))
    monkeypatch.chdir(tmp_path)  # keine cwd-Config

    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "unified-gui.config.json").write_text(json.dumps({
        "title": "Shared-Titel",
        "ollama": {"url": "http://shared:1"},
        "bach": {"rest_url": "http://shared:8000"},
    }), encoding="utf-8")
    (user_dir / "unified-gui.config.json").write_text(json.dumps({
        "ollama": {"url": "http://user:2"},
    }), encoding="utf-8")
    (user_dir / f"unified-gui.config.{hostname()}.json").write_text(json.dumps({
        "ollama": {"url": "http://host:3"},
    }), encoding="utf-8")

    cfg = UnifiedGuiConfig.load()
    assert cfg.title == "Shared-Titel"              # aus Shared-Basis
    assert cfg.bach.rest_url == "http://shared:8000"  # Shared gilt, wo nichts drueber liegt
    assert cfg.ollama.url == "http://host:3"        # Host-Datei gewinnt ueber User/Shared


def test_discovery_fills_missing_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("UNIFIED_GUI_CONFIG", str(tmp_path / "leer.json"))
    monkeypatch.delenv("UNIFIED_GUI_DISCOVERY", raising=False)
    cfg = UnifiedGuiConfig.load()
    # Discovery liefert ~-Notation, die expandiert wird — kein "~" mehr im Ergebnis
    assert cfg.bach.bach_root and str(Path.home()) in cfg.bach.bach_root
    assert cfg.clutch.module_id == "clutch"


def test_discovery_no_longer_guesses_a_bare_onedrive_module_path(monkeypatch, tmp_path):
    """T-20260902-901571937: `clutch.repo_path`/`lock_master.module_path` used
    to have a bare "~/OneDrive/..." discovery default -- filled into `data`
    BEFORE resolve_module_path() runs, so it looked exactly like an explicit
    user config and permanently outranked the (correct) catalog/hardcode-guard
    resolution under the fixed precedence. Removed; both fields are resolved
    exclusively by resolve_module_path() (+ the lock-master hardcode guard)
    now. In full isolation (no catalog, isolated in conftest.py) clutch has
    no fallback -- its module_id is filled by discovery.module_id="clutch"
    but resolve_module_path() can find no clone for it, so it stays absent
    rather than pointing at a possibly-empty OneDrive read copy."""
    monkeypatch.setenv("UNIFIED_GUI_CONFIG", str(tmp_path / "leer.json"))
    monkeypatch.delenv("UNIFIED_GUI_DISCOVERY", raising=False)
    cfg = UnifiedGuiConfig.load()
    assert cfg.clutch.repo_path is None
    assert cfg.ticket_master.config_dir is None


def test_discovery_respects_explicit_none(monkeypatch, tmp_path):
    monkeypatch.setenv("UNIFIED_GUI_CONFIG", str(tmp_path / "leer.json"))
    monkeypatch.delenv("UNIFIED_GUI_DISCOVERY", raising=False)
    cfg = UnifiedGuiConfig.load(overrides={"bach": {"bach_root": None}})
    assert cfg.bach.bach_root is None  # explizites null bleibt (kein Discovery-Override)


def test_discovery_off_switch(monkeypatch, tmp_path):
    monkeypatch.setenv("UNIFIED_GUI_CONFIG", str(tmp_path / "leer.json"))
    monkeypatch.setenv("UNIFIED_GUI_DISCOVERY", "0")
    cfg = UnifiedGuiConfig.load()
    assert cfg.clutch.repo_path is None
    assert cfg.bach.bach_root is None


def _no_db_env(monkeypatch):
    monkeypatch.delenv("TASKPLAN_DB", raising=False)
    monkeypatch.delenv("RINNSAL_DB", raising=False)


def test_scanner_db_follows_taskplan_config(monkeypatch):
    """Die TASKPLAN-Konfiguration schlaegt den Altpfad — sonst driftet die GUI weg."""
    _no_db_env(monkeypatch)
    taskplan_client = pytest.importorskip("taskplan.client")
    monkeypatch.setattr(taskplan_client, "configured_db_path", lambda: "/aus/der/toml.db")
    assert scanner_db_default() == "/aus/der/toml.db"


def test_scanner_db_env_beats_config(monkeypatch):
    monkeypatch.setenv("TASKPLAN_DB", "/env/db.sqlite")
    assert scanner_db_default() == "/env/db.sqlite"


def test_scanner_db_falls_back_to_legacy_path(monkeypatch):
    """Ohne TASKPLAN-Konfiguration bleibt die GUI beim Altpfad.

    Bewusst NICHT bei ~/.taskplan/taskplan.db, worauf get_default_db_path()
    zeigen wuerde: die ist im Bestand leer — die GUI zeigte dann ohne Fehler
    und ohne Warnung eine leere Queue.
    """
    _no_db_env(monkeypatch)
    taskplan_client = pytest.importorskip("taskplan.client")
    monkeypatch.setattr(taskplan_client, "configured_db_path", lambda: "")
    assert scanner_db_default() == SCANNER_DB_FALLBACK


def test_scanner_db_without_taskplan_installed(monkeypatch):
    """Fremdes System ohne TASKPLAN: Import scheitert -> Altpfad, kein Crash."""
    _no_db_env(monkeypatch)
    monkeypatch.setitem(sys.modules, "taskplan.client", None)  # Import wirft
    assert scanner_db_default() == SCANNER_DB_FALLBACK


def test_discovery_resolves_scanner_db(monkeypatch, tmp_path):
    """Der Discovery-Default wird beim Laden ausgewertet, nicht beim Import."""
    monkeypatch.setenv("UNIFIED_GUI_CONFIG", str(tmp_path / "leer.json"))
    monkeypatch.delenv("UNIFIED_GUI_DISCOVERY", raising=False)
    monkeypatch.setenv("TASKPLAN_DB", str(tmp_path / "aus-env.db"))
    cfg = UnifiedGuiConfig.load()
    assert cfg.scanner_tasks.db_path == str(tmp_path / "aus-env.db")


def test_explicit_fallback_beats_the_catalog(monkeypatch, tmp_path):
    """T-20260902-901571937: an explicit local configuration must win over
    the catalog even when the catalog has a fully resolvable entry for the
    same module -- the old precedence let a merely-existing OneDrive
    directory silently overrule a deliberately configured local clone."""
    catalog_module_dir = tmp_path / ".MODULES" / ".CONTROL" / "lock-master"
    catalog_module_dir.mkdir(parents=True)
    catalog_path = tmp_path / ".MODULES" / "modules.catalog.json"
    catalog_path.write_text(json.dumps({
        "schema": "ellmos.modules-catalog.v1",
        "modules": [{
            "id": "lock-master",
            "resolved_source": ".CONTROL/lock-master",
            "runtime_source": str(catalog_module_dir),
        }],
    }), encoding="utf-8")
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(catalog_path))
    explicit = str(tmp_path / "explicit-local-clone")

    resolved = resolve_module_path("lock-master", explicit)

    assert resolved == explicit


def test_module_id_resolves_from_catalog_runtime_source_when_no_fallback(monkeypatch, tmp_path):
    module_dir = tmp_path / "_Local_DEV" / "repos" / "lock-master"
    module_dir.mkdir(parents=True)
    catalog_path = tmp_path / ".MODULES" / "modules.catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps({
        "schema": "ellmos.modules-catalog.v1",
        "modules": [{
            "id": "lock-master",
            "resolved_source": ".CONTROL/lock-master",
            "runtime_source": str(module_dir),
        }],
    }), encoding="utf-8")
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(catalog_path))

    resolved = resolve_module_path("lock-master", None)

    assert resolved == str(module_dir)


def test_catalog_resolved_source_is_never_used_as_a_load_path(monkeypatch, tmp_path, capsys):
    """T-20260902-901571937: `resolved_source` is the OneDrive-relative
    catalog find location, never a runtime import path. A module with no
    verified local clone (`runtime_source` absent) must resolve to no path
    at all -- not silently to its OneDrive resolved_source -- and the
    refusal must be visible, not swallowed."""
    onedrive_dir = tmp_path / "OneDrive-mirror" / ".CONTROL" / "lock-master"
    onedrive_dir.mkdir(parents=True)
    catalog_path = tmp_path / "OneDrive-mirror" / "modules.catalog.json"
    catalog_path.write_text(json.dumps({
        "schema": "ellmos.modules-catalog.v1",
        "modules": [{"id": "lock-master", "resolved_source": ".CONTROL/lock-master"}],
    }), encoding="utf-8")
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(catalog_path))

    resolved = resolve_module_path("lock-master", None)

    assert resolved is None
    assert "lock-master" in capsys.readouterr().err


def test_module_id_keeps_legacy_path_as_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(tmp_path / "missing.json"))
    fallback = str(tmp_path / "legacy")
    assert resolve_module_path("missing-module", fallback) == fallback
