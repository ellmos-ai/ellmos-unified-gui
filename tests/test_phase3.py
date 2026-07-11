# SPDX-License-Identifier: MIT
"""Phase 3: Routing-Config-Roundtrip (ticket-master) + Modell-Adapter-Degradierung."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.clutch import ClutchAdapter
from unified_gui.adapters.controlcenter import ControlCenterAdapter
from unified_gui.adapters.ollama import OllamaAdapter
from unified_gui.adapters.ticket_master import TicketMasterAdapter
from unified_gui.config import (ClutchConfig, ControlCenterConfig, OllamaConfig,
                                TicketMasterConfig)


@pytest.fixture
def tm(tmp_path):
    tickets = tmp_path / "TICKETS"
    tickets.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "ticket-master.config.example.json").write_text(json.dumps({
        "providers": {"claude": {"default_model": "sonnet"}, "codex": {}, "agy": {}},
        "default_provider": "claude",
        "score_thresholds": {"tier1_max": 8, "tier2_max": 12, "tier3_max": 28, "tier4_min": 29},
        "advisor": {"enabled": False, "model": "opus", "threshold_score": 35},
        "router_command": None,
    }), encoding="utf-8")
    return TicketMasterAdapter(TicketMasterConfig(
        tickets_root=str(tickets), config_dir=str(config_dir)))


def test_routing_config_defaults_without_file(tm):
    cfg = tm.routing_config()
    assert cfg["config_exists"] is False
    assert cfg["score_thresholds"]["tier4_min"] == 29
    assert cfg["default_provider"] == "claude"


def test_routing_config_write_creates_from_example(tm, tmp_path):
    result = tm.set_routing_config({
        "default_provider": "codex",
        "score_thresholds": {"tier1_max": 6},
    })
    assert result["config_exists"] is True
    assert result["default_provider"] == "codex"
    assert result["score_thresholds"]["tier1_max"] == 6
    assert result["score_thresholds"]["tier4_min"] == 29  # aus example gemerged

    written = json.loads((tmp_path / "config" / "ticket-master.config.json")
                         .read_text(encoding="utf-8"))
    assert written["providers"]["claude"]["default_model"] == "sonnet"  # example uebernommen


def test_routing_config_rejects_bad_thresholds(tm):
    with pytest.raises(AdapterError):
        tm.set_routing_config({"score_thresholds": {"tier1_max": 40}})


def test_routing_config_rejects_unknown_field(tm):
    with pytest.raises(AdapterError):
        tm.set_routing_config({"providers": {}})


def test_clutch_probe_missing():
    adapter = ClutchAdapter(ClutchConfig(repo_path="/nonexistent"))
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_ollama_probe_dead():
    adapter = OllamaAdapter(OllamaConfig(url="http://127.0.0.1:1", timeout_s=0.2))
    assert adapter.probe() == set()
    with pytest.raises(AdapterError):
        adapter.models()


def test_controlcenter_probe_missing():
    adapter = ControlCenterAdapter(ControlCenterConfig(repo_path="/nonexistent"))
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_score_preview_uses_written_config(tm):
    tm.set_routing_config({"default_provider": "codex",
                           "advisor": {"threshold_score": 20, "enabled": True}})
    suggestion = tm.score_preview(clarity=2, complexity=8, creativity=3, context=4, criticality=5)
    assert suggestion.provider == "codex"
    assert suggestion.advisor is True  # 28 >= 20
