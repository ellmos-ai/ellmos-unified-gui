# SPDX-License-Identifier: MIT
"""Host-Auth-Adapter: liest die eingeloggte Person + Rolle des Host-Auftritts
(z. B. ellmos-core), wenn die Unified GUI dort per mount() eingehaengt ist.

Kein eigenes Login, keine zweite Nutzerverwaltung -- die Wahrheit bleibt beim
Host: `ellmos_core.web.get_current_user()` liest ausschliesslich
`request.session` (vom Host per SessionMiddleware gesetzt) + die Host-eigene
`users`-Tabelle. Fehlt der Host oder die Session, degradiert die Rueckgabe auf
`None` statt zu werfen (ADAPTER-CONTRACT.md §5).

Absichtlich KEIN Bestandteil von `panel.required`: Panels bleiben ohne
Host-Auth voll sichtbar (BACH-Mount/Standalone unveraendert) -- diese
Capability wird ausschliesslich fuer optionales Write-Gating konsultiert
(siehe p5_permissions.py). `mount()` doku eigen: "Auth uebernimmt der Host" --
dieser Adapter erweitert das um feingranulares Gating INNERHALB eines Panels,
ohne die grobe Zugriffsentscheidung (eingeloggt ja/nein) neu zu erfinden.
"""
from __future__ import annotations

from typing import Any

from ..capabilities import Capability, HealthInfo
from .base import BaseAdapter


class HostAuthAdapter(BaseAdapter):
    name = "host-auth"
    label = "Host-Anmeldung"

    def probe(self) -> set[Capability]:
        try:
            import ellmos_core.web  # noqa: F401
        except ImportError:
            return set()
        return {Capability.AUTH_ROLE}

    def health(self) -> HealthInfo:
        try:
            import ellmos_core  # noqa: F401
        except ImportError:
            return HealthInfo(status="offline",
                              detail="ellmos-core nicht im Prozess (Standalone- oder Fremd-Mount)")
        return HealthInfo(status="ok", detail="ellmos-core-Session verfuegbar")

    def current_user(self, request: Any) -> dict | None:
        """Liest die eingeloggte Person aus der Host-Session. Wirft NIE
        (ADAPTER-CONTRACT.md §5) -- kein Host, keine Session oder ein
        fachlicher Fehler liefern gleichermassen `None` (= "kein Nutzerkontext,
        Gating entfaellt"), nie eine Ausnahme."""
        try:
            from ellmos_core.web import get_current_user
        except ImportError:
            return None
        try:
            return get_current_user(request)
        except Exception:  # noqa: BLE001 -- Degradierung statt Crash (ADAPTER-CONTRACT §5)
            return None
