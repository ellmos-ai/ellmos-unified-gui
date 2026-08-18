# SPDX-License-Identifier: MIT
"""P12 Races: End-to-End gegen die volle create_app()-Verdrahtung -- beweist,
dass compare_race_adapter tatsaechlich registriert, sichtbar und ueber HTTP
erreichbar ist (nicht nur der Adapter isoliert, siehe test_compare_race_adapter.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from starlette.testclient import TestClient

from unified_gui.web.app import create_app

COMPARE_RACE_REPO = Path(__file__).parent.parent.parent / "compare-race"

pytestmark = pytest.mark.skipif(
    not (COMPARE_RACE_REPO / "src" / "compare_race" / "report.py").is_file(),
    reason="compare-race-Repo (report.py) nicht vorhanden",
)

_RACE_MD = """---
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
"""

_RUN_MD = """---
race_id: {race_id}
time_token: 20260816-000000
prompt_token: test
system: TESTHOST
model: opus-5
run: 1
variant: base
backend: claude
mode: sequential
started_utc: 2026-08-16T00:00:00Z
finished_utc: 2026-08-16T00:01:00Z
latency_s: 1.0
ok: true
cost_gear: test-gear
est_cost_usd: 0.0
checks_passed: []
checks_failed: []
---

Testantwort.
"""


@pytest.fixture
def races_dir(tmp_path):
    root = tmp_path / "races"
    race_id = "20260816-000000--e2e-test"
    race_dir = root / race_id
    race_dir.mkdir(parents=True)
    (race_dir / "PROMPT.md").write_text("E2E-Testprompt.", encoding="utf-8")
    (race_dir / "RACE.md").write_text(_RACE_MD.format(race_id=race_id), encoding="utf-8")
    (race_dir / "RUN-opus-5-r1.md").write_text(_RUN_MD.format(race_id=race_id), encoding="utf-8")
    return root


def _app(races_dir):
    return create_app(
        config={"compare_race": {"repo_path": str(COMPARE_RACE_REPO), "races_dir": str(races_dir)}},
        standalone_guard=False,
    )


def test_p12_appears_in_visible_panels_when_races_dir_configured(races_dir):
    client = TestClient(_app(races_dir))
    status = client.get("/api/status").json()
    assert "p12" in status["panels"]
    assert "races.ro" in status["available"]


def test_p12_absent_without_races_dir():
    app = create_app(config={"compare_race": {"repo_path": str(COMPARE_RACE_REPO), "races_dir": None}},
                      standalone_guard=False)
    client = TestClient(app)
    status = client.get("/api/status").json()
    assert "p12" not in status["panels"]


def test_p12_races_endpoint_lists_the_real_fixture(races_dir):
    client = TestClient(_app(races_dir))
    resp = client.get("/api/p12/races")
    assert resp.status_code == 200
    races = resp.json()
    assert len(races) == 1
    assert races[0]["race_id"] == "20260816-000000--e2e-test"
    assert races[0]["run_count"] == 1


def test_p12_race_detail_endpoint_reads_real_run_headers(races_dir):
    client = TestClient(_app(races_dir))
    resp = client.get("/api/p12/races/20260816-000000--e2e-test")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["runs"][0]["model"] == "opus-5"
    assert "# RACE" in detail["race_md"]


def test_p12_race_detail_unknown_id_is_409_not_500(races_dir):
    client = TestClient(_app(races_dir))
    resp = client.get("/api/p12/races/ghost-race")
    assert resp.status_code == 409


def test_p12_page_renders_when_capability_present(races_dir):
    client = TestClient(_app(races_dir))
    resp = client.get("/p12")
    assert resp.status_code == 200
    assert "Races" in resp.text


def test_p12_page_redirects_when_capability_absent():
    app = create_app(config={"compare_race": {"repo_path": str(COMPARE_RACE_REPO), "races_dir": None}},
                      standalone_guard=False)
    client = TestClient(app, follow_redirects=False)
    resp = client.get("/p12")
    assert resp.status_code == 302
