# SPDX-License-Identifier: MIT
"""decisions-Adapter: Sicht auf die TO-DECIDE-Kette, lesend und (falls verfuegbar) schreibend.

Zwei getrennt geprobte Teilfaehigkeiten:

* **DECISIONS_RO** — die generierte `decisions.index.json` (Schema
  `decisions.index/1`) ist lesbar. Reicht fuer die reine Uebersicht.
* **DECISIONS_RW** — zusaetzlich ist die Kernlogik des Moduls
  `decision-clicker` importierbar und die Kette bedienbar. Dann kann das
  Panel Entscheidungen eintragen, neue einstellen und das Desktop-Postfach
  uebernehmen.

**Der Adapter parst nichts selbst.** Er delegiert an `decision_clicker`, das
seinerseits den kanonischen Generator `_DECISIONS/_tools/decisions_index.py`
als Modul laedt. Damit bleibt genau ein Parser im Umlauf — die Begruendung
aus [D10] gilt unveraendert, nur der Weg dorthin ist jetzt ein Modul statt
einer JSON-Datei. Siehe [D11].

**Im RW-Betrieb wird frisch aus der Kette gelesen, nicht aus der JSON.** Ein
Klick schreibt an eine Zeilennummer; eine veraltete Index-Datei wuerde auf
die falsche Stelle zeigen. Zusaetzlich prueft der Schreibpfad die erwartete
ID an der Zielzeile (`expected_id`) und bricht bei Abweichung ab.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..capabilities import Capability, HealthInfo
from ..config import DecisionsConfig
from .base import AdapterError, BaseAdapter

SCHEMA = "decisions.index/1"

# Anzeigereihenfolge: offen zuerst, dann entschieden-mit-offener-Umsetzung.
# DONE/ARCHIVIERT werden ohne expliziten status_class-Filter ausgeblendet,
# sonst fluten sie die Ansicht (im Live-Index 140 von 194 Eintraegen).
STATUS_ORDER = ("OFFEN", "ENTSCHIEDEN_UMSETZUNG_OFFEN", "DONE", "ARCHIVIERT")
DEFAULT_VISIBLE_STATUS = ("OFFEN", "ENTSCHIEDEN_UMSETZUNG_OFFEN")


@dataclass
class _Cache:
    mtime: float = 0.0
    data: dict | None = None
    error: str | None = None


class DecisionsAdapter(BaseAdapter):
    name = "decisions"
    label = "Decisions (TO-DECIDE-Index, read-only)"

    def __init__(self, config: DecisionsConfig | None = None) -> None:
        self.config = config or DecisionsConfig()
        self._cache = _Cache()
        self._clicker: Any | None = None
        self._clicker_error: str | None = None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _path(self) -> Path | None:
        if not self.config.index_path:
            return None
        return Path(self.config.index_path).expanduser()

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            if self._load() is not None:
                caps.add(Capability.DECISIONS_RO)
        except Exception:  # noqa: BLE001 -- probe() wirft nie
            pass
        try:
            clicker = self._load_clicker()
            if clicker is not None and clicker.usable():
                caps.add(Capability.DECISIONS_RW)
                caps.add(Capability.DECISIONS_RO)  # RW impliziert die Lesesicht
        except Exception:  # noqa: BLE001
            pass
        return caps

    # ------------------------------------------------------------------
    # decision-clicker-Kernlogik laden (optional)
    # ------------------------------------------------------------------
    def _load_clicker(self) -> Any | None:
        """`decision_clicker.api.DecisionClicker` — oder None, wenn nicht da.

        Fehlt das Modul, bleibt der Adapter exakt der read-only-Adapter von
        vorher. Das ist der Degradierungspfad aus [D03].
        """
        if self._clicker is not None or self._clicker_error is not None:
            return self._clicker
        repo = self.config.clicker_path
        if not repo:
            self._clicker_error = "clicker_path nicht konfiguriert"
            return None
        src = Path(repo).expanduser() / "src"
        if not (src / "decision_clicker" / "api.py").is_file():
            self._clicker_error = f"{src} enthaelt kein decision_clicker/api.py"
            return None
        try:
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))
            spec = importlib.util.find_spec("decision_clicker.api")
            if spec is None:
                raise ImportError("decision_clicker.api nicht auffindbar")
            module = importlib.import_module("decision_clicker.api")
            self._clicker = module.DecisionClicker(self.config.chain_dir)
        except Exception as exc:  # noqa: BLE001 -- Degradierung statt Crash
            self._clicker_error = f"{type(exc).__name__}: {exc}"
            return None
        return self._clicker

    def _require_clicker(self) -> Any:
        clicker = self._load_clicker()
        if clicker is None:
            raise AdapterError("decisions.readonly",
                               self._clicker_error or "Schreibpfad nicht verfuegbar")
        return clicker

    @staticmethod
    def _wrap(fn):
        """Fehler der Kernlogik als AdapterError — Panels rendern sie inline."""
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except AdapterError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise AdapterError(f"decisions.{type(exc).__name__}", str(exc)) from exc
        return call

    def health(self) -> HealthInfo:
        clicker = self._load_clicker()
        if clicker is not None:
            try:
                werte = clicker.status()
                detail = (f"{werte['chain_dir']} — {werte['counts']['offen']} offen, "
                          f"{werte['intake_pending']} im Postfach (schreibend)")
                if werte["foreign_locks"]:
                    return HealthInfo("degraded",
                                      f"{detail}; fremde Sperre: {', '.join(werte['foreign_locks'])}")
                return HealthInfo("ok", detail)
            except Exception as exc:  # noqa: BLE001 -- health() wirft nie
                return HealthInfo("degraded", f"decision-clicker: {type(exc).__name__}: {exc}")

        path = self._path()
        if path is None:
            return HealthInfo("offline", "index_path nicht konfiguriert")
        if not path.is_file():
            return HealthInfo("offline", f"{path} nicht gefunden")
        try:
            data = self._load()
        except Exception as exc:  # noqa: BLE001 -- health() soll ebenfalls nie werfen
            return HealthInfo("degraded", f"{path}: {type(exc).__name__}: {exc}")
        if data is None:
            hint = self._cache.error or "ungueltiges Schema"
            return HealthInfo("degraded", f"{path}: {hint}")
        counts = data.get("counts") or {}
        detail = f"{path} ({counts.get('total', '?')} Eintraege, generiert {data.get('generated_at', '?')})"
        return HealthInfo("ok", detail)

    # ------------------------------------------------------------------
    # Read-only Zugriff (kein IndexStore-Protokoll im ADAPTER-CONTRACT --
    # P10 ist neu; die Methoden sind bewusst schmal gehalten)
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        """Kopf des Index (Zaehler, Kollisionen, Quelldateien) -- ohne entries[]."""
        data = self._load() or {}
        return {
            "generated_at": data.get("generated_at"),
            "generator": data.get("generator"),
            "root": data.get("root"),
            "counts": data.get("counts") or {},
            "collisions": data.get("collisions") or [],
            "files": data.get("files") or [],
        }

    def scopes(self) -> list[str]:
        """Distinkte scope-Werte -- fuer das Filter-Dropdown."""
        data = self._load() or {}
        by_scope = (data.get("counts") or {}).get("by_scope") or {}
        if by_scope:
            return sorted(by_scope.keys())
        return sorted({e.get("scope") for e in (data.get("entries") or []) if e.get("scope")})

    def entries(self, scope: str | None = None, status_class: str | None = None) -> list[dict]:
        """Gefilterte, sortierte Sicht auf entries[].

        Ohne status_class-Filter: nur OFFEN + ENTSCHIEDEN_UMSETZUNG_OFFEN,
        OFFEN zuerst -- DONE/ARCHIVIERT nur gezaehlt (summary()), nicht
        prominent gezeigt. Mit explizitem status_class-Filter wird genau
        dieser Status geliefert (auch DONE/ARCHIVIERT).
        Felder koennen leer/None sein -- defensiv gelesen, unbekannte
        Felder werden unveraendert durchgereicht (vorwaertskompatibel).
        """
        data = self._load() or {}
        rows = list(data.get("entries") or [])
        if scope:
            rows = [r for r in rows if r.get("scope") == scope]
        if status_class:
            rows = [r for r in rows if r.get("status_class") == status_class]
        else:
            rows = [r for r in rows if r.get("status_class") in DEFAULT_VISIBLE_STATUS]
        order = {name: i for i, name in enumerate(STATUS_ORDER)}
        rows.sort(key=lambda r: (
            order.get(r.get("status_class"), len(order)),
            r.get("date") or "",
            r.get("key") or r.get("id") or "",
        ))
        return rows

    def collisions(self) -> list[dict]:
        data = self._load() or {}
        return list(data.get("collisions") or [])

    # ------------------------------------------------------------------
    # Interaktiv (nur bei DECISIONS_RW) -- alles delegiert an decision_clicker
    # ------------------------------------------------------------------
    def status(self) -> dict:
        """Live-Zaehler direkt aus der Kette, plus Postfach- und Sperrlage."""
        return self._wrap(self._require_clicker().status)()

    def open_entries(self) -> list[dict]:
        """Offene Entscheidungen FRISCH aus der Kette (nicht aus der JSON)."""
        return self._wrap(self._require_clicker().open_entries)()

    def detail(self, key: str) -> dict:
        """Ein Eintrag mit Volltext, aufgeloesten Optionen und Empfehlung."""
        return self._wrap(self._require_clicker().detail)(key)

    def decide(self, key: str, choice: str, note: str = "") -> dict:
        return self._wrap(self._require_clicker().decide)(key, choice, note)

    def create(self, title: str, **felder) -> dict:
        return self._wrap(self._require_clicker().create)(title, **felder)

    def register(self, query: str = "") -> list[dict]:
        return self._wrap(self._require_clicker().register)(query)

    def intake_pending(self) -> list[dict]:
        return self._wrap(self._require_clicker().intake_pending)()

    def intake_apply(self) -> list[dict]:
        return self._wrap(self._require_clicker().intake_apply)()

    def chain_dir(self) -> str | None:
        """Kettenordner — Root fuer die Rechtepruefung in P10."""
        clicker = self._load_clicker()
        if clicker is not None:
            return str(clicker.settings.chain_dir)
        return self.config.chain_dir

    # ------------------------------------------------------------------
    # intern -- mtime-Cache
    # ------------------------------------------------------------------
    def _load(self) -> dict | None:
        path = self._path()
        if path is None or not path.is_file():
            self._cache = _Cache()
            return None
        try:
            mtime = path.stat().st_mtime
        except OSError as exc:
            self._cache = _Cache(error=f"{type(exc).__name__}: {exc}")
            return None
        if self._cache.data is not None and self._cache.mtime == mtime:
            return self._cache.data
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._cache = _Cache(error=f"{type(exc).__name__}: {exc}")
            return None
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or "entries" not in raw:
            self._cache = _Cache(error=f"unerwartetes Schema (erwartet {SCHEMA})")
            return None
        self._cache = _Cache(mtime=mtime, data=raw)
        return raw
