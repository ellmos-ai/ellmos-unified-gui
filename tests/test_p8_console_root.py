"""Die Tickets-Wurzel des P8-Konsolen-Spikes darf keinen fremden Nutzerpfad raten.

Regression: `console/p8_tickets_console.py` trug einen fest verdrahteten
`C:\\Users\\<name>\\OneDrive\\...`-Default. Auf jedem anderen Rechner zeigte der Default ins
Leere, und in einem zur Veroeffentlichung vorgesehenen Baum ist ein absoluter Benutzerpfad
zugleich Instanzdaten.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

CONSOLE = Path(__file__).resolve().parents[1] / "console" / "p8_tickets_console.py"


def _load():
    spec = importlib.util.spec_from_file_location("p8_tickets_console", CONSOLE)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("p8_tickets_console", module)
    spec.loader.exec_module(module)
    return module


def test_quelle_enthaelt_keinen_absoluten_benutzerpfad():
    source = CONSOLE.read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\+Users\\+", source), "absoluter Windows-Benutzerpfad im Spike"
    assert not re.search(r"/(?:home|Users)/[A-Za-z0-9_.-]+", source), "absoluter POSIX-Heimpfad im Spike"


def test_explizite_umgebungsvariable_gewinnt(monkeypatch, tmp_path):
    monkeypatch.setenv("UNIFIED_GUI_TICKETS_ROOT", str(tmp_path))
    assert _load().default_tickets_root() == str(tmp_path)


def test_ohne_hinweis_kein_geratener_pfad(monkeypatch):
    for var in ("UNIFIED_GUI_TICKETS_ROOT", "TICKETS_ROOT", "OneDrive", "OneDriveConsumer"):
        monkeypatch.delenv(var, raising=False)
    assert _load().default_tickets_root() is None


def test_root_wird_pflichtargument_wenn_nichts_aufloesbar(monkeypatch, capsys):
    for var in ("UNIFIED_GUI_TICKETS_ROOT", "TICKETS_ROOT", "OneDrive", "OneDriveConsumer"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(SystemExit):
        _load().main([])
    assert "--root" in capsys.readouterr().err
