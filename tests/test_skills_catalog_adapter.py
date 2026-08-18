# SPDX-License-Identifier: MIT
"""SkillsCatalogAdapter: Fetch/Fixture-artiges Setup wie test_lock_master_adapter.py,
aber hier gegen eine ECHTE Kopie von catalog.py + TEMPLATE_SKILL.md aus dem
kanonischen Klon C:\\_Local_DEV\\repos\\skills -- create()/set_description()
laufen also gegen die reale Logik (parse_frontmatter eingeschlossen), nicht
gegen ein Double. Nur `testing/skill_tester.py` ist ein Stub (siehe
_write_stub_tester) -- der echte S-Test hat eigene Abhaengigkeiten, die hier
nicht Testgegenstand sind; Testgegenstand ist, dass der Adapter korrekt
aufruft/den Exit-Code/das Ergebnis-JSON richtig interpretiert.

Wenn der kanonische skills-Klon auf diesem System fehlt, werden diese Tests
uebersprungen (gleiche Konvention wie test_p5_role_gating.py fuer lock-master).
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.skills_catalog import SkillsCatalogAdapter
from unified_gui.config import SkillsCatalogConfig

SKILLS_REPO = Path(__file__).parent.parent.parent / "skills"

pytestmark = pytest.mark.skipif(
    not (SKILLS_REPO / "catalog.py").is_file(),
    reason="skills-Repo (catalog.py) nicht vorhanden",
)


def _write_stub_tester(repo: Path) -> None:
    """Ersetzt NUR testing/skill_tester.py durch einen deterministischen Stub,
    der genau das Ergebnisformat schreibt, das catalog.py's cmd_quality selbst
    liest (results/<name>/<ts>.json mit quality_score/rating/dimensions)."""
    testing_dir = repo / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)
    (testing_dir / "skill_tester.py").write_text(
        'import json, sys, time\n'
        'from pathlib import Path\n'
        'name = sys.argv[2]\n'
        'out_dir = Path(__file__).parent / "results" / name\n'
        'out_dir.mkdir(parents=True, exist_ok=True)\n'
        'data = {"quality_score": 4.2, "rating": "gut", '
        '"dimensions": {"d1_clarity": 4}, "meta": {"date": "2026-08-18"}}\n'
        '(out_dir / f"{int(time.time()*1000)}.json").write_text(json.dumps(data), encoding="utf-8")\n'
        'sys.exit(0)\n',
        encoding="utf-8",
    )


@pytest.fixture
def repo(tmp_path):
    """Bewusst MINIMAL statt eine Kopie der echten 435-Skill-Bibliothek: nur
    catalog.py + das Template werden gebraucht, damit create()/set_description()
    gegen echten Code laufen. Ein Voll-Copytree wäre pro Test langsam UND
    würde suggerieren, dass diese Tests die reale Bibliothek brauchen -- tun
    sie nicht (isolierte sandbox-category reicht, siehe Modul-Docstring)."""
    dest = tmp_path / "skills"
    dest.mkdir()
    shutil.copy2(SKILLS_REPO / "catalog.py", dest / "catalog.py")
    templates_dest = dest / "skills" / "_templates"
    templates_dest.mkdir(parents=True)
    shutil.copy2(SKILLS_REPO / "skills" / "_templates" / "TEMPLATE_SKILL.md",
                 templates_dest / "TEMPLATE_SKILL.md")
    _write_stub_tester(dest)
    return dest


@pytest.fixture
def adapter(repo):
    return SkillsCatalogAdapter(SkillsCatalogConfig(repo_path=str(repo), timeout_s=20.0))


def test_probe_finds_catalog_py(adapter):
    from unified_gui.capabilities import Capability
    assert Capability.SKILLS_CREATE in adapter.probe()


def test_probe_empty_without_repo():
    adapter = SkillsCatalogAdapter(SkillsCatalogConfig(repo_path="/does/not/exist"))
    assert adapter.probe() == set()


def test_categories_lists_non_underscore_dirs(adapter, repo):
    (repo / "skills" / "sandbox-category").mkdir(parents=True, exist_ok=True)
    cats = adapter.categories()
    names = [c["name"] for c in cats]
    assert "sandbox-category" in names
    assert "_templates" not in names


def test_create_writes_a_real_skill_md(adapter, repo):
    result = adapter.create("test-wizard-skill", "sandbox-category", "skill")
    skill_file = Path(result["path"])
    assert skill_file.is_file()
    text = skill_file.read_text(encoding="utf-8")
    assert "name: test-wizard-skill" in text
    assert "type: skill" in text


def test_create_rejects_non_kebab_case_name(adapter):
    with pytest.raises(AdapterError, match="invalid_name"):
        adapter.create("Not Kebab Case", "sandbox-category", "skill")


def test_create_refuses_existing_directory(adapter, repo):
    adapter.create("dup-skill", "sandbox-category", "skill")
    with pytest.raises(AdapterError, match="create_failed"):
        adapter.create("dup-skill", "sandbox-category", "skill")


def test_set_description_roundtrips_through_real_parse_frontmatter(adapter, repo):
    adapter.create("describe-me", "sandbox-category", "skill")
    result = adapter.set_description(
        "describe-me", "sandbox-category",
        "Formatiert CSV-Dateien nach einem festen Schema. "
        "Nutze diesen Skill, wenn CSV-Spalten umbenannt oder neu sortiert werden sollen.",
    )
    assert "Formatiert CSV-Dateien" in result["description"]

    # Beweis, nicht Annahme: ueber catalog.py's EIGENEN Parser zurueckgelesen.
    import importlib.util
    spec = importlib.util.spec_from_file_location("catalog_ro", repo / "catalog.py")
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    skill_file = repo / "skills" / "sandbox-category" / "describe-me" / "SKILL.md"
    parsed = catalog.parse_frontmatter(skill_file)
    assert parsed["description"] == result["description"]


def test_set_description_folds_embedded_newlines(adapter, repo):
    """Der Fall, den ein naiver String-Replace bricht: eingebettete \\n im
    Nutzertext duerfen die Folgezeilen-Einrueckung nicht zerstoeren."""
    adapter.create("newline-skill", "sandbox-category", "skill")
    result = adapter.set_description(
        "newline-skill", "sandbox-category",
        "Erste Zeile.\nZweite Zeile mit mehr Text als in die erste passt.",
    )
    assert "\n" not in result["description"]
    assert "Erste Zeile. Zweite Zeile" in result["description"]

    skill_file = repo / "skills" / "sandbox-category" / "newline-skill" / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    # Jede Fortsetzungszeile unter description: > bleibt eingerueckt --
    # keine Zeile beginnt an Spalte 0 innerhalb des description-Blocks.
    in_block = False
    for line in text.splitlines():
        if line.startswith("description:"):
            in_block = True
            continue
        if in_block:
            if line.strip() == "" or not line.startswith(" "):
                break
            assert line.startswith("  ")


def test_set_description_missing_skill_raises(adapter):
    with pytest.raises(AdapterError, match="skill_not_found"):
        adapter.set_description("ghost-skill", "sandbox-category", "irrelevant")


def test_quality_runs_stub_tester_and_reads_result(adapter, repo):
    adapter.create("quality-skill", "sandbox-category", "skill")
    result = adapter.quality("quality-skill")
    assert result["quality_score"] == 4.2
    assert result["rating"] == "gut"
    assert result["exit_code"] == 0
