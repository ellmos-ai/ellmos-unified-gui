# SPDX-License-Identifier: MIT
"""P14 Governance: unveraenderter Read-only-Konsum des MCP-Lesespiegels.

Die fachlichen Status- und Vollstaendigkeitsentscheidungen bleiben beim
ControlCenter-MCP. Dieses Panel transportiert und rendert nur dessen fertigen
Markdown-Bericht; es parst oder rekonstruiert keine Governance-Daten.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unified_gui.adapters.controlcenter import ControlCenterAdapter
from unified_gui.capabilities import Capability, HealthInfo
from unified_gui.config import ControlCenterConfig
from unified_gui.web import app as app_module


REPORT_CASES = (
    (
        "available",
        """# Federated governance metadata (read-only)

- Aggregate: **COMPLETE**
- Complete: yes

| Source | Status | Detail |
|---|---|---|
| decisions | available | stale: no; entries: 11 |
| policy_registry | available | norms: 26; BYUM candidates: 0 |
""",
    ),
    (
        "unconfigured",
        """# Federated governance metadata (read-only)

- Aggregate: **UNKNOWN**
- Complete: no

| Source | Status | Detail |
|---|---|---|
| decisions | unconfigured | stale: no; entries: 0 |
| policy_registry | unconfigured | norms: 0; BYUM candidates: 0 |
""",
    ),
    (
        "unreadable",
        """# Federated governance metadata (read-only)

- Aggregate: **PARTIAL**
- Complete: no

| Source | Status | Detail |
|---|---|---|
| decisions | available | stale: yes; entries: 1 |
| policy_registry | unreadable | norms: 0; BYUM candidates: 0 |
""",
    ),
    (
        "invalid",
        """# Federated governance metadata (read-only)

- Aggregate: **PARTIAL**
- Complete: no

| Source | Status | Detail |
|---|---|---|
| decisions | invalid | stale: unknown; entries: 0 |
| policy_registry | available | norms: 1; BYUM candidates: 0 |
""",
    ),
)


class FakeControlCenterAdapter:
    name = "controlcenter"
    label = "ControlCenter-MCP (Governance)"
    report = REPORT_CASES[0][1]

    def __init__(self, _config=None) -> None:
        pass

    def probe(self):
        return {Capability.GOVERNANCE_RO}

    def health(self):
        return HealthInfo("ok", "fake")

    def governance(self):
        return {
            "text": self.report,
            "media_type": "text/markdown",
            "read_only": True,
        }


def test_controlcenter_probe_exposes_governance_capability(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.js").write_text("controlcenter_list_governance", encoding="utf-8")
    monkeypatch.setattr("unified_gui.adapters.controlcenter.shutil.which", lambda _exe: "node")
    adapter = ControlCenterAdapter(ControlCenterConfig(repo_path=str(tmp_path)))

    assert Capability.GOVERNANCE_RO in adapter.probe()


def test_controlcenter_probe_hides_governance_when_built_server_is_stale(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.js").write_text("controlcenter_list_skills", encoding="utf-8")
    monkeypatch.setattr("unified_gui.adapters.controlcenter.shutil.which", lambda _exe: "node")
    adapter = ControlCenterAdapter(ControlCenterConfig(repo_path=str(tmp_path)))

    capabilities = adapter.probe()

    assert Capability.SKILLS_DISCOVERY in capabilities
    assert Capability.GOVERNANCE_RO not in capabilities


def test_adapter_calls_exact_governance_tool_and_returns_typed_read_only_report(monkeypatch):
    adapter = ControlCenterAdapter(ControlCenterConfig())
    calls = []

    def fake_call(tool, arguments=None):
        calls.append((tool, arguments))
        return {"text": REPORT_CASES[0][1]}

    monkeypatch.setattr(adapter, "_call", fake_call)

    report = adapter.governance()

    assert calls == [("controlcenter_list_governance", None)]
    assert report.text == REPORT_CASES[0][1]
    assert report.media_type == "text/markdown"
    assert report.read_only is True


@pytest.mark.parametrize(("source_status", "report"), REPORT_CASES)
def test_panel_preserves_source_and_completeness_states(monkeypatch, source_status, report):
    FakeControlCenterAdapter.report = report
    monkeypatch.setattr(app_module, "ControlCenterAdapter", FakeControlCenterAdapter)
    client = TestClient(app_module.create_app(config={}, standalone_guard=False))

    status = client.get("/api/status").json()
    response = client.get("/api/p14/governance")

    assert "p14" in status["panels"]
    assert "governance.ro" in status["available"]
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "text": report,
        "media_type": "text/markdown",
        "read_only": True,
    }
    assert source_status in payload["text"]


def test_panel_keeps_partial_stale_and_valid_zero_distinct(monkeypatch):
    FakeControlCenterAdapter.report = REPORT_CASES[2][1]
    monkeypatch.setattr(app_module, "ControlCenterAdapter", FakeControlCenterAdapter)
    client = TestClient(app_module.create_app(config={}, standalone_guard=False))

    partial_text = client.get("/api/p14/governance").json()["text"]
    FakeControlCenterAdapter.report = REPORT_CASES[0][1]
    complete_text = client.get("/api/p14/governance").json()["text"]

    assert "Aggregate: **PARTIAL**" in partial_text
    assert "Complete: no" in partial_text
    assert "stale: yes" in partial_text
    assert "Aggregate: **COMPLETE**" in complete_text
    assert "Complete: yes" in complete_text
    assert "policy_registry | available | norms: 26; BYUM candidates: 0" in complete_text


def test_panel_template_escapes_report_and_explains_read_only_boundary():
    template = (
        Path(__file__).parent.parent
        / "src"
        / "unified_gui"
        / "web"
        / "templates"
        / "p14_governance.html"
    ).read_text(encoding="utf-8")

    assert "esc(data.text)" in template
    assert "read-only" in template
    assert "advisory pointer" in template
    assert "Übernehmen" not in template
    assert "Ausführen" not in template
