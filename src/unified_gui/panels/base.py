# SPDX-License-Identifier: MIT
"""Panel-Vertrag: ein Panel = Capabilities + Router + Template."""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter

from ..capabilities import Capability


@dataclass
class PanelSpec:
    id: str                    # "p5"
    label: str                 # Nav-Beschriftung
    path: str                  # Seitenpfad, z. B. "/p5"
    template: str              # Template-Dateiname
    required: set[Capability] = field(default_factory=set)
    router: APIRouter | None = None
