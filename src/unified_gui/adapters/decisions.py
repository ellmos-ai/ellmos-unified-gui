# SPDX-License-Identifier: MIT
"""decisions-Adapter: read-only Sicht auf den generierten TO-DECIDE-Index.

Liest ausschliesslich die bereits erzeugte `decisions.index.json`
(Schema `decisions.index/1`, Generator unter
`_control-center/_DECISIONS/_tools/`). Der Adapter haelt KEINE zweite
Quelle der Wahrheit: er kennt die TO-DECIDE-*.txt-Quelldateien nicht,
schreibt nie, und liest bei jedem Aufruf frisch (mtime-Cache spart nur
das wiederholte Parsen derselben unveraenderten Datei).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import DecisionsConfig
from .base import BaseAdapter

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

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _path(self) -> Path | None:
        if not self.config.index_path:
            return None
        return Path(self.config.index_path).expanduser()

    def probe(self) -> set[Capability]:
        try:
            data = self._load()
        except Exception:  # noqa: BLE001 -- probe() wirft nie
            return set()
        return {Capability.DECISIONS_RO} if data is not None else set()

    def health(self) -> HealthInfo:
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
