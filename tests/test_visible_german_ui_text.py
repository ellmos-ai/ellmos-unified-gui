# SPDX-License-Identifier: MIT
"""Regressionstests für sichtbare deutsche Statushinweise der Operatoroberfläche."""

import json
import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unified_gui.adapters.bach import BachAdapter
from unified_gui.adapters.decisions import DecisionsAdapter, SCHEMA
from unified_gui.adapters.host_auth import HostAuthAdapter
from unified_gui.adapters.lock_master import LockMasterAdapter
from unified_gui.config import BachConfig, DecisionsConfig, LockMasterConfig


def test_visible_adapter_statuses_use_real_german_umlauts(tmp_path, monkeypatch):
    system_dir = tmp_path / "bach" / "system"
    system_dir.mkdir(parents=True)
    (system_dir / "bach.py").write_text("# stub", encoding="utf-8")
    bach = BachAdapter(BachConfig(
        bach_root=str(system_dir.parent),
        rest_url="http://127.0.0.1:1",
        rest_timeout_s=0.2,
    ))
    bach.probe()

    index_path = tmp_path / "decisions.index.json"
    index_path.write_text(json.dumps({
        "schema": SCHEMA,
        "generated_at": "2026-08-29T12:00:00",
        "counts": {"total": 2},
        "entries": [],
    }), encoding="utf-8")
    decisions = DecisionsAdapter(DecisionsConfig(index_path=str(index_path)))

    lock_master = LockMasterAdapter(LockMasterConfig())
    lock_master._engine = ModuleType("permissions")

    monkeypatch.setitem(sys.modules, "ellmos_core", ModuleType("ellmos_core"))
    host_auth = HostAuthAdapter()

    details = {
        "bach": bach.health().detail,
        "decisions": decisions.health().detail,
        "lock_master": lock_master.health().detail,
        "host_auth": host_auth.health().detail,
    }

    assert "Agenten via CLI verfügbar" in details["bach"]
    assert "2 Einträge" in details["decisions"]
    assert "über Engine nicht verfügbar" in details["lock_master"]
    assert details["host_auth"] == "ellmos-core-Session verfügbar"
    assert not any(
        spelling in detail
        for detail in details.values()
        for spelling in ("verfuegbar", "Eintraege", "ueber")
    )
