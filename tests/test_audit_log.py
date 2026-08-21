# SPDX-License-Identifier: MIT
"""audit_log.py: der JSONL-Writer selbst, isoliert von der Middleware."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unified_gui.audit_log import (
    DEFAULT_AUDIT_LOG,
    append_audit_entry,
    is_audit_disabled,
    resolve_audit_log_path,
)


def test_default_path_is_under_home_ellmos_not_onedrive():
    assert DEFAULT_AUDIT_LOG == Path.home() / ".ellmos" / "unified-gui" / "audit.jsonl"
    assert "OneDrive" not in str(DEFAULT_AUDIT_LOG)


def test_explicit_override_wins_over_env(monkeypatch):
    monkeypatch.setenv("UNIFIED_GUI_AUDIT_LOG", "/env/path.jsonl")
    assert resolve_audit_log_path("/explicit/path.jsonl") == "/explicit/path.jsonl"


def test_env_wins_over_default(monkeypatch):
    monkeypatch.setenv("UNIFIED_GUI_AUDIT_LOG", "/env/path.jsonl")
    assert resolve_audit_log_path(None) == "/env/path.jsonl"


def test_default_when_nothing_set(monkeypatch):
    monkeypatch.delenv("UNIFIED_GUI_AUDIT_LOG", raising=False)
    assert resolve_audit_log_path(None) == str(DEFAULT_AUDIT_LOG)


def test_is_audit_disabled_recognizes_off_case_insensitive():
    assert is_audit_disabled("off")
    assert is_audit_disabled("OFF")
    assert is_audit_disabled("  Off  ")
    assert not is_audit_disabled("/some/path.jsonl")


def test_append_writes_one_json_line(tmp_path):
    target = tmp_path / "sub" / "audit.jsonl"
    status, error = append_audit_entry({"a": 1}, str(target))
    assert status == "written"
    assert error is None
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"a": 1}


def test_append_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "does" / "not" / "exist" / "audit.jsonl"
    append_audit_entry({"a": 1}, str(target))
    assert target.is_file()


def test_append_is_append_only_not_overwrite(tmp_path):
    target = tmp_path / "audit.jsonl"
    append_audit_entry({"seq": 1}, str(target))
    append_audit_entry({"seq": 2}, str(target))
    lines = target.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["seq"] for line in lines] == [1, 2]


def test_off_disables_without_writing(tmp_path):
    target = tmp_path / "audit.jsonl"
    status, error = append_audit_entry({"a": 1}, "off")
    assert status == "disabled"
    assert error is None
    assert not target.exists()


def test_write_failure_reports_failed_not_raise(tmp_path):
    # Ziel ist eine Datei, kein Verzeichnis -- mkdir(parents=True) auf einen
    # Elternteil, der bereits eine DATEI ist, scheitert kontrolliert.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    target = blocker / "audit.jsonl"
    status, error = append_audit_entry({"a": 1}, str(target))
    assert status == "failed"
    assert error is not None


def test_entry_never_needs_argument_values_to_be_meaningful():
    """Nicht funktional erzwungen (der Aufrufer entscheidet, was er uebergibt),
    aber die dokumentierte Konvention wird hier als Beispiel festgehalten:
    ein Eintrag traegt nur Argumentnamen, nie -werte."""
    entry = {"argument_keys": ["name", "category"], "argument_count": 2}
    assert "argument_values" not in entry
