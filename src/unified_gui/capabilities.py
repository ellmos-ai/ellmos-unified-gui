# SPDX-License-Identifier: MIT
"""Capability-Modell der Unified GUI.

Adapter melden per probe(), welche Capabilities ihr Backend JETZT anbietet.
Panels deklarieren required_capabilities; die Registry entscheidet, welche
Panels sichtbar werden. Spezifikation: docs/ADAPTER-CONTRACT.md.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .adapters.base import BaseAdapter


class Capability(str, Enum):
    """Additiv-stabile Faehigkeits-Kennungen (nie umbenennen/loeschen)."""

    PROMPTS_RW = "prompts.rw"
    PROMPTS_VERSIONS = "prompts.versions"
    PROMPTS_IMPORT = "prompts.import"
    AGENT_DISPATCH = "agent.dispatch"
    AGENT_STEER = "agent.steer"
    MODELS_LOCAL = "models.local"
    MODELS_API = "models.api"
    ROUTING_CONFIG = "routing.config"
    ROUTING_STATS = "routing.stats"
    PERMISSIONS_RW = "permissions.rw"
    LOCKS_RW = "locks.rw"
    SCHEDULER_RW = "scheduler.rw"
    TASKS_RO = "tasks.ro"
    TASKS_ASSIGN = "tasks.assign"
    TICKETS_RW = "tickets.rw"
    SKILLS_DISCOVERY = "skills.discovery"
    SKILLS_CREATE = "skills.create"
    DECISIONS_RO = "decisions.ro"
    DECISIONS_RW = "decisions.rw"
    AUTH_ROLE = "auth.role"
    RACES_RO = "races.ro"
    # Wheelhouse M1 (T-20260825-835413946): ellmos-chat als optionaler
    # chat.runtime-Provider -- Backend-agnostische Chat-Runtime, siehe
    # adapters/ellmos_chat.py.
    CHAT_RUNTIME = "chat.runtime"


@dataclass
class HealthInfo:
    """Status eines Backends fuer die GUI-Statusleiste."""

    status: str = "offline"  # "ok" | "degraded" | "offline"
    detail: str = ""
    version: str | None = None
    latency_ms: int | None = None


@dataclass
class AdapterState:
    adapter: "BaseAdapter"
    capabilities: set[Capability] = field(default_factory=set)
    probe_error: str | None = None
    probed_at: float = 0.0


class CapabilityRegistry:
    """Haelt Adapter + deren geprobte Capabilities. Kein globaler Zustand —
    jede App-Instanz besitzt ihre eigene Registry (Doppel-Mount-Regel)."""

    def __init__(self) -> None:
        self._states: dict[str, AdapterState] = {}

    def register(self, adapter: "BaseAdapter") -> AdapterState:
        state = AdapterState(adapter=adapter)
        self._states[adapter.name] = state
        self._probe(state)
        return state

    def _probe(self, state: AdapterState) -> None:
        """Vertrag: probe() darf nie werfen — zur Sicherheit fangen wir trotzdem.
        Fehler => leere Capability-Menge (Backend gilt als abwesend)."""
        try:
            state.capabilities = set(state.adapter.probe())
            state.probe_error = None
        except Exception as exc:  # noqa: BLE001 — bewusst breit (Degradierung statt Crash)
            state.capabilities = set()
            state.probe_error = f"{type(exc).__name__}: {exc}"
        state.probed_at = time.time()

    def refresh(self) -> None:
        for state in self._states.values():
            self._probe(state)

    @property
    def available(self) -> set[Capability]:
        caps: set[Capability] = set()
        for state in self._states.values():
            caps |= state.capabilities
        return caps

    @property
    def states(self) -> list[AdapterState]:
        return list(self._states.values())

    def adapter(self, name: str) -> "BaseAdapter | None":
        state = self._states.get(name)
        return state.adapter if state else None

    def find(self, cap: Capability) -> "BaseAdapter | None":
        """Erster Adapter, der die Capability anbietet."""
        for state in self._states.values():
            if cap in state.capabilities:
                return state.adapter
        return None

    def supports(self, required: set[Capability]) -> bool:
        return required <= self.available
