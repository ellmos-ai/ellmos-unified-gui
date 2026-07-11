# SPDX-License-Identifier: MIT
"""Cloud-/Multi-System-Konfiguration: Expansion, Kaskade, Host-Override, Discovery."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.config import UnifiedGuiConfig, _expand, hostname, resolve_module_path


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
    assert cfg.clutch.repo_path and "~" not in cfg.clutch.repo_path
    assert cfg.bach.bach_root and str(Path.home()) in cfg.bach.bach_root


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


def test_module_id_resolves_from_catalog_before_legacy_path(monkeypatch, tmp_path):
    module_dir = tmp_path / ".MODULES" / ".CONTROL" / "lock-master"
    module_dir.mkdir(parents=True)
    catalog_path = tmp_path / ".MODULES" / "modules.catalog.json"
    catalog_path.write_text(json.dumps({
        "schema": "ellmos.modules-catalog.v1",
        "modules": [{"id": "lock-master", "resolved_source": ".CONTROL/lock-master"}],
    }), encoding="utf-8")
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(catalog_path))

    resolved = resolve_module_path("lock-master", "/legacy/lock-master")
    assert resolved == str(module_dir)


def test_module_id_keeps_legacy_path_as_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("ELLMOS_MODULES_CATALOG", str(tmp_path / "missing.json"))
    fallback = str(tmp_path / "legacy")
    assert resolve_module_path("missing-module", fallback) == fallback
