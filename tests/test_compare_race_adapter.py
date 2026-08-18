# SPDX-License-Identifier: MIT
"""CompareRaceAdapter: read-only Race-Report-Zugriff.

Wie test_skills_catalog_adapter.py laufen diese Tests gegen den ECHTEN
`compare_race.report`-Code aus dem kanonischen Klon (C:\\_Local_DEV\\repos\\compare-race)
-- read_race_dir() wird also wirklich ausgefuehrt, nicht gedoubelt. Die
Race-Ordner selbst sind Fixtures (tmp_path), nicht die echten User-Races --
so bleiben die Tests deterministisch und unabhaengig vom tatsaechlichen
Race-Bestand auf diesem Host. Wenn der kanonische Klon fehlt (report.py oder
system_auditor nicht importierbar), werden diese Tests uebersprungen (gleiche
Konvention wie test_skills_catalog_adapter.py fuer lock-master/skills).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.compare_race import CompareRaceAdapter
from unified_gui.config import CompareRaceConfig

COMPARE_RACE_REPO = Path(__file__).parent.parent.parent / "compare-race"


def _report_importable() -> bool:
    if not (COMPARE_RACE_REPO / "src" / "compare_race" / "report.py").is_file():
        return False
    try:
        sys.path.insert(0, str(COMPARE_RACE_REPO / "src"))
        import compare_race.report  # noqa: F401
    except Exception:  # noqa: BLE001 -- z. B. system_auditor fehlt
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _report_importable(),
    reason="compare-race-Repo (report.py + system_auditor) nicht importierbar",
)

_RUN_TEMPLATE = """---
race_id: {race_id}
time_token: 20260816-000000
prompt_token: test
system: TESTHOST
model: {model}
run: {run}
variant: base
backend: claude
mode: sequential
started_utc: 2026-08-16T00:00:00Z
finished_utc: 2026-08-16T00:01:00Z
latency_s: 12.5
ok: true
cost_gear: test-gear
est_cost_usd: 0.01
checks_passed: []
checks_failed: []
---

Testantwort des Modells {model}.
"""

_RACE_MD_TEMPLATE = """---
race_id: {race_id}
time_token: 20260816-000000
prompt_token: test
system: TESTHOST
mode: sequential
lanes: 1
failed: 0
judge: starter
---

# RACE {race_id}

## Prompt (Task)

> Testprompt.
"""


@pytest.fixture
def races_dir(tmp_path):
    root = tmp_path / "races"
    root.mkdir()
    race_id = "20260816-000000--test-race"
    race_dir = root / race_id
    race_dir.mkdir()
    (race_dir / "PROMPT.md").write_text("Testprompt fuer den Adapter-Test.", encoding="utf-8")
    (race_dir / "RACE.md").write_text(_RACE_MD_TEMPLATE.format(race_id=race_id), encoding="utf-8")
    (race_dir / "RUN-opus-5-r1.md").write_text(
        _RUN_TEMPLATE.format(race_id=race_id, model="opus-5", run=1), encoding="utf-8")
    (race_dir / "RUN-codex-r1.md").write_text(
        _RUN_TEMPLATE.format(race_id=race_id, model="codex", run=1), encoding="utf-8")
    # Ein zweiter, unvollstaendiger Ordner (kein RACE.md) -- muss in races()
    # als solcher erkennbar sein, ohne den Adapter zu werfen.
    (root / "20260816-000001--unfertig").mkdir()
    return root


@pytest.fixture
def adapter(races_dir):
    return CompareRaceAdapter(CompareRaceConfig(repo_path=str(COMPARE_RACE_REPO), races_dir=str(races_dir)))


def test_probe_finds_races_dir_and_report_module(adapter):
    from unified_gui.capabilities import Capability
    assert Capability.RACES_RO in adapter.probe()


def test_probe_empty_without_races_dir():
    adapter = CompareRaceAdapter(CompareRaceConfig(repo_path=str(COMPARE_RACE_REPO), races_dir="/does/not/exist"))
    assert adapter.probe() == set()


def test_probe_empty_without_repo_path(races_dir):
    adapter = CompareRaceAdapter(CompareRaceConfig(repo_path=None, races_dir=str(races_dir)))
    assert adapter.probe() == set()


def test_health_ok_reports_races_dir(adapter, races_dir):
    health = adapter.health()
    assert health.status == "ok"
    assert str(races_dir) in health.detail


def test_races_lists_newest_first_with_prompt_preview(adapter):
    races = adapter.races()
    ids = [r["race_id"] for r in races]
    assert ids == ["20260816-000001--unfertig", "20260816-000000--test-race"]
    complete = next(r for r in races if r["race_id"] == "20260816-000000--test-race")
    assert complete["has_race_md"] is True
    assert complete["run_count"] == 2
    assert "Testprompt" in complete["prompt_preview"]
    incomplete = next(r for r in races if r["race_id"] == "20260816-000001--unfertig")
    assert incomplete["has_race_md"] is False


def test_race_detail_reads_real_read_race_dir(adapter):
    detail = adapter.race_detail("20260816-000000--test-race")
    assert detail["race_id"] == "20260816-000000--test-race"
    assert "# RACE" in detail["race_md"]
    models = sorted(r["model"] for r in detail["runs"])
    assert models == ["codex", "opus-5"]
    # _body wird nicht durchgereicht (Panel zeigt RACE.md als Ganzes, nicht
    # jeden Run-Volltext einzeln -- haelt die Antwort kompakt).
    assert all("_body" not in r for r in detail["runs"])


def test_race_detail_missing_race_raises(adapter):
    with pytest.raises(AdapterError, match="race_not_found"):
        adapter.race_detail("does-not-exist")


def test_race_detail_rejects_path_traversal(adapter):
    with pytest.raises(AdapterError, match="invalid_race_id"):
        adapter.race_detail("../../etc")
