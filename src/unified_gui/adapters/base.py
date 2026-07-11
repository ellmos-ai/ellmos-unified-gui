# SPDX-License-Identifier: MIT
"""Adapter-Basisvertrag. Spezifikation: docs/ADAPTER-CONTRACT.md.

Regeln:
- probe() antwortet schnell (< 2 s) und wirft NIE (Fehler => leere Menge).
- Panels sprechen ausschliesslich Adapter an, nie Backends direkt.
- Adapter halten keine zweite Quelle der Wahrheit (nur Views/Edits am Backend).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..capabilities import Capability, HealthInfo


class AdapterError(Exception):
    """Fachlicher Adapterfehler — Panels rendern kind/hint inline, nie als 500."""

    def __init__(self, kind: str, hint: str = "") -> None:
        super().__init__(f"{kind}: {hint}" if hint else kind)
        self.kind = kind
        self.hint = hint


class BaseAdapter(ABC):
    name: str = "base"
    label: str = "Base"

    @abstractmethod
    def probe(self) -> set[Capability]:
        """Faehigkeiten, die das Backend JETZT anbietet (nie werfen!)."""

    @abstractmethod
    def health(self) -> HealthInfo:
        """Status fuer die GUI-Leiste (ok/degraded/offline + Hinweis)."""
