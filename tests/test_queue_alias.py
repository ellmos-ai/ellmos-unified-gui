"""Rename-Toleranz fuer die Ticket-Queue (T-20260906-387521104).

Die Live-Queue `_control-center/_TICKETS` wird nach `TICKETS` umbenannt.
Ordner und die Configs, die darauf zeigen, liegen in OneDrive und replizieren
mit eigener Latenz -- ein Rechner kann also den einen Namen konfiguriert und
den anderen auf der Platte haben.

Diese GUI liest nur, richtet also keinen Schaden an. Ohne Toleranz zeigte sie
aber schlicht "keine Tickets" -- und das sieht aus wie eine leere Queue statt
wie ein falscher Pfad. Genau diese Verwechslung fangen die Tests hier ab.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from unified_gui.config import resolve_queue_alias  # noqa: E402


def test_old_name_redirects_when_only_new_exists(tmp_path):
    new = tmp_path / "TICKETS"
    new.mkdir()

    assert resolve_queue_alias(str(tmp_path / "_TICKETS")) == str(new)


def test_new_name_redirects_when_only_old_exists(tmp_path):
    old = tmp_path / "_TICKETS"
    old.mkdir()

    assert resolve_queue_alias(str(tmp_path / "TICKETS")) == str(old)


def test_existing_directory_wins(tmp_path):
    old = tmp_path / "_TICKETS"
    old.mkdir()

    assert resolve_queue_alias(str(old)) == str(old)


def test_both_present_keeps_the_requested_one(tmp_path):
    """Nicht raten: bei einer Split-Queue bleibt die Anfrage stehen.

    Die GUI liest nur -- ein Abbruch waere hier unverhaeltnismaessig, aber
    stillschweigend die andere Haelfte zu waehlen waere schlimmer: der Nutzer
    saehe eine plausible, aber unvollstaendige Queue.
    """
    old = tmp_path / "_TICKETS"
    new = tmp_path / "TICKETS"
    old.mkdir()
    new.mkdir()

    assert resolve_queue_alias(str(old)) == str(old)
    assert resolve_queue_alias(str(new)) == str(new)


def test_neither_present_is_unchanged(tmp_path):
    asked = str(tmp_path / "_TICKETS")

    assert resolve_queue_alias(asked) == asked


def test_unrelated_path_is_untouched(tmp_path):
    other = str(tmp_path / "tickets")

    assert resolve_queue_alias(other) == other


def test_empty_values_pass_through():
    assert resolve_queue_alias(None) is None
    assert resolve_queue_alias("") == ""
