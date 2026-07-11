# SPDX-License-Identifier: MIT
"""BACH-Adapter: JSON-Extraktion aus verrauschter CLI-Ausgabe + Degradierung."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.bach import BachAdapter, extract_json
from unified_gui.adapters.base import AdapterError
from unified_gui.config import BachConfig


def test_extract_json_clean():
    assert extract_json('{"ok": true}') == {"ok": True}


def test_extract_json_with_hook_noise():
    noisy = (
        "[ProSync] ProSync: Keine neueren Backups im Transit\n"
        '{"agents": [{"name": "demo", "running": false}], "active_count": 0}\n'
        "[CLOCK] 22:15\n"
        "[ProSync] ProSync Push: Bereits heute gepusht\n"
    )
    data = extract_json(noisy)
    assert data["active_count"] == 0
    assert data["agents"][0]["name"] == "demo"


def test_extract_json_multiline_payload():
    noisy = '[Hook] x\n{\n  "action": "start",\n  "agent": {"pid": 42}\n}\n[Ende]'
    assert extract_json(noisy)["agent"]["pid"] == 42


def test_extract_json_none_raises():
    with pytest.raises(AdapterError):
        extract_json("[ProSync] nur Rauschen, kein JSON")


def test_probe_all_absent():
    adapter = BachAdapter(BachConfig(bach_root="/nonexistent",
                                     rest_url="http://127.0.0.1:1", rest_timeout_s=0.2))
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_probe_cli_only(tmp_path):
    system = tmp_path / "system"
    system.mkdir()
    (system / "bach.py").write_text("# stub", encoding="utf-8")
    adapter = BachAdapter(BachConfig(bach_root=str(tmp_path),
                                     rest_url="http://127.0.0.1:1", rest_timeout_s=0.2))
    caps = adapter.probe()
    assert "agent.dispatch" in {c.value for c in caps}
    assert "scheduler.rw" not in {c.value for c in caps}
    assert adapter.health().status == "degraded"
