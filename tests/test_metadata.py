"""Contract tests for Pfad B metadata saturation, Level 1 SBOM, and documentation parity."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).parent.parent


def test_notice_file_exists_and_attributed() -> None:
    notice_file = ROOT / "NOTICE"
    assert notice_file.is_file(), "NOTICE file must exist in the root"
    content = notice_file.read_text(encoding="utf-8")
    assert "Lukas Geiger" in content
    assert "ellmos-ai" in content
    assert "open-bricks" in content
    assert "MIT License" in content


def test_third_party_licenses_text_companion_exists() -> None:
    sbom_txt = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert sbom_txt.is_file(), "THIRD_PARTY_LICENSES.txt must exist as Level 1 SBOM companion"
    content = sbom_txt.read_text(encoding="utf-8")
    assert "LEVEL 1 SOFTWARE BILL OF MATERIALS (SBOM)" in content
    assert "RunAsInvoker" in content
    assert "Zero-Copyleft" in content
    assert "521 BGB" in content
    assert "48-Hour" in content or "48h" in content
    for expected_inv in (
        "INV-LOCAL-01",
        "INV-CANON-02",
        "INV-PROBE-03",
        "INV-AUDIT-04",
        "INV-LOCK-05",
        "INV-INJECT-06",
        "INV-MOUNT-07",
        "INV-HOST-08",
        "INV-ZERO-09",
        "INV-SLA-10",
    ):
        assert expected_inv in content, f"Invariant {expected_inv} missing in SBOM text companion"


def test_pep621_twenty_keywords() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    keywords = pyproject["project"].get("keywords", [])
    assert len(keywords) == 20, f"Expected 20 saturated keywords in pyproject.toml, got {len(keywords)}"
    assert len(set(keywords)) == 20, "Keywords must be unique"
    for expected_kw in ("desktop-app", "operator-console", "zero-egress", "local-first", "modular-ui"):
        assert expected_kw in keywords, f"Keyword '{expected_kw}' missing"


def test_pep621_license_files_includes_notice_and_sbom() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    license_files = pyproject["project"].get("license-files", [])
    assert "LICENSE" in license_files
    assert "NOTICE" in license_files
    assert "THIRD_PARTY_LICENSES.md" in license_files
    assert "THIRD_PARTY_LICENSES.txt" in license_files


def test_pep621_project_urls_complete() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    urls = pyproject["project"].get("urls", {})
    required_keys = (
        "Repository",
        "Documentation",
        "Changelog",
        "Security",
        "Notice",
        "Third-Party Licenses",
        "Third-Party Licenses (Text)",
        "Level 1 SBOM",
    )
    for key in required_keys:
        assert key in urls, f"Project URL '{key}' missing in pyproject.toml"


def test_dual_html_anchors_sec01_to_sec18() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")
    for sec_num in range(1, 19):
        anchor = f'<a id="sec-{sec_num:02d}"></a>'
        assert anchor in readme_en, f"Anchor {anchor} missing in README.md"
        assert anchor in readme_de, f"Anchor {anchor} missing in README_de.md"


def test_german_statutory_notice_bilingual() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")
    assert "§ 521 BGB" in readme_en
    assert "§ 521 BGB" in readme_de
    assert "48" in readme_en
    assert "48" in readme_de


def test_mermaid_diagrams_present_in_both_readmes() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")
    for doc in (readme_en, readme_de):
        assert "```mermaid" in doc
        assert "flowchart TD" in doc
        assert "sequenceDiagram" in doc
        assert "autonumber" in doc


def test_marketing_log_exists_and_current() -> None:
    marketing_log = ROOT / "MARKETING-LOG.txt"
    assert marketing_log.is_file(), "MARKETING-LOG.txt must exist"
    content = marketing_log.read_text(encoding="utf-8")
    assert "2026-10-03" in content
    assert "320" in content  # clone traffic metric
    assert "[PERSONA-01]" in content
    assert "[PERSONA-04]" in content
    assert "REC-20261003-01" in content


def test_changelog_has_unreleased_pfad_b_entry() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in changelog
    assert "Pfad B Discoverability" in changelog or "Pfad B" in changelog
    assert "Level 1 SBOM" in changelog


def test_llms_txt_reflects_current_test_count_and_version() -> None:
    llms_txt = (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "v0.9.0" in llms_txt
    assert "280 tests" in llms_txt
    assert "NOTICE" in llms_txt
    assert "THIRD_PARTY_LICENSES.txt" in llms_txt
