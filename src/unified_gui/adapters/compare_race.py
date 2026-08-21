# SPDX-License-Identifier: MIT
"""compare-race-Adapter: read-only Race-Report-Browser.

Schliesst den read-only Teil des Anwendungsfalls "Modelle gegeneinander
antreten lassen" an die Konsole an. Bewusste Grenze:

- Race-Daten sind bereits real vorhanden (races_dir, echte PROMPT.md/RACE.md/
  RUN-*.md aus mehreren Modellen) -- das Lesen ist ein normaler, sicherer
  Panel-Schritt wie skills-catalog/ticket-master/decisions.
- Ein Race STARTEN oder das Judge-Urteil AUTOMATISIEREN ist dagegen keine
  reine Verdrahtungsfrage: compare-race ist bewusst LLM-in-the-loop
  (Urteil = modellmanuell, Default "der Starter" -- system_auditor-Muster
  "die Bibliothek bereitet vor, das Modell urteilt"), und ein Web-Panel, das
  auf Klick echte Mehrmodell-API-Kosten ausloest, ist eine Produkt-/
  Kostenentscheidung, keine Implementierungsdetail. Deshalb bewusst NUR
  read_race_dir() angebunden -- kein `run`/`record`/`olympiade`.

Wiederverwendung statt Neubau: `compare_race.report.read_race_dir()` wird
per Paket-Import aus dem konfigurierten Klon genutzt (sys.path-Erweiterung
um <repo>/src, dann regulaerer Paket-Import -- report.py hat relative
Imports und interne Abhaengigkeiten auf system_auditor, ein einzelner
importlib.spec_from_file_location auf die Datei allein wuerde daran
scheitern). `system_auditor` selbst muss separat importierbar sein (siehe
compare-race README: `pip install -e system-auditor`) -- probe() meldet das
ehrlich als "offline", statt einen ImportError als 500 zu zeigen.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from ..capabilities import Capability, HealthInfo
from ..config import CompareRaceConfig
from .base import AdapterError, BaseAdapter

_RACE_ID_RE_INVALID = ("/", "\\", "..")


class CompareRaceAdapter(BaseAdapter):
    name = "compare-race"
    label = "compare-race (Race-Reports, read-only)"

    def __init__(self, config: CompareRaceConfig | None = None) -> None:
        self.config = config or CompareRaceConfig()
        self._report_module: ModuleType | None = None
        self._import_error: str | None = None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _races_dir(self) -> Path | None:
        if not self.config.races_dir:
            return None
        path = Path(self.config.races_dir).expanduser()
        return path if path.is_dir() else None

    def probe(self) -> set[Capability]:
        try:
            ready = self._races_dir() is not None and self._read_race_dir_fn() is not None
        except Exception as exc:  # noqa: BLE001 -- probe wirft nie
            self._import_error = f"{type(exc).__name__}: {exc}"
            ready = False
        return {Capability.RACES_RO} if ready else set()

    def health(self) -> HealthInfo:
        races_dir = self._races_dir()
        if races_dir is None:
            return HealthInfo("offline", f"races_dir nicht gefunden: {self.config.races_dir}")
        try:
            self._read_race_dir_fn()
        except Exception as exc:  # noqa: BLE001 -- Health darf nie werfen
            return HealthInfo("offline", f"{type(exc).__name__}: {exc}")
        return HealthInfo("ok", str(races_dir))

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def _read_race_dir_fn(self):
        if self._report_module is None:
            repo = self.config.repo_path
            if not repo:
                raise AdapterError("compare_race_repo_missing", "repo_path nicht konfiguriert")
            src = str(Path(repo).expanduser() / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            self._report_module = importlib.import_module("compare_race.report")
        return self._report_module.read_race_dir

    @staticmethod
    def _validate_race_id(race_id: str) -> None:
        if not race_id or any(bad in race_id for bad in _RACE_ID_RE_INVALID):
            raise AdapterError("invalid_race_id", repr(race_id))

    # ------------------------------------------------------------------
    # Lesend
    # ------------------------------------------------------------------
    def races(self) -> list[dict[str, Any]]:
        """Listet alle Race-Ordner (neueste zuerst) mit Kopfdaten aus PROMPT.md."""
        races_dir = self._races_dir()
        if races_dir is None:
            raise AdapterError("races_dir_missing", str(self.config.races_dir))
        out: list[dict[str, Any]] = []
        for item in sorted(races_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not item.is_dir():
                continue
            race_md = item / "RACE.md"
            prompt_md = item / "PROMPT.md"
            prompt_preview = ""
            if prompt_md.is_file():
                text = prompt_md.read_text(encoding="utf-8", errors="replace").strip()
                prompt_preview = text[:160]
            out.append({
                "race_id": item.name,
                "has_race_md": race_md.is_file(),
                "run_count": len(list(item.glob("RUN-*.md"))),
                "prompt_preview": prompt_preview,
            })
        return out

    def race_detail(self, race_id: str) -> dict[str, Any]:
        """RACE.md-Volltext (inkl. Judge-Urteil, falls ausgefuellt) + Run-Kopfdaten
        ueber `read_race_dir()` -- reines Lesen bestehender Artefakte, kein Trigger."""
        self._validate_race_id(race_id)
        races_dir = self._races_dir()
        if races_dir is None:
            raise AdapterError("races_dir_missing", str(self.config.races_dir))
        race_dir = races_dir / race_id
        race_md = race_dir / "RACE.md"
        if not race_md.is_file():
            raise AdapterError("race_not_found", str(race_dir))
        read_race_dir = self._read_race_dir_fn()
        runs = read_race_dir(race_dir)
        return {
            "race_id": race_id,
            "race_md": race_md.read_text(encoding="utf-8"),
            "runs": [{k: v for k, v in r.items() if k != "_body"} for r in runs],
        }
