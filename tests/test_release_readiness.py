"""Regression tests for public-readiness metadata and documentation."""

from __future__ import annotations

import ast
import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).parent.parent
REPOSITORY_URL = "https://github.com/ellmos-ai/unified-gui"


def test_version_surfaces_agree() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_init = ast.parse(
        (ROOT / "src/unified_gui/__init__.py").read_text(encoding="utf-8")
    )
    package_version = next(
        ast.literal_eval(node.value)
        for node in package_init.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        )
    )
    assert metadata["project"]["version"] == package_version
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == package_version


def test_canonical_repository_is_declared() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "ellmos-module.v2.json").read_text(encoding="utf-8"))
    assert metadata["project"]["urls"]["Repository"] == REPOSITORY_URL
    assert manifest["source_of_truth"]["repository"] == REPOSITORY_URL


def test_release_hygiene_files_exist() -> None:
    required = (
        "SECURITY.md",
        ".github/workflows/ci.yml",
        ".github/workflows/codeql.yml",
    )
    assert all((ROOT / relative).is_file() for relative in required)


def test_todo_exposes_machine_readable_status_table() -> None:
    todo = (ROOT / "TODO.md").read_text(encoding="utf-8")
    assert "## STATUS" in todo
    assert "| Category | Status | Evidence / next gate |" in todo


def test_german_readme_uses_real_umlauts() -> None:
    readme = (ROOT / "README_de.md").read_text(encoding="utf-8")
    for transliteration in ("unabhaengig", "ergaenzt", "ueberall"):
        assert transliteration not in readme
    assert all(character in readme for character in "äöü")
