# SPDX-License-Identifier: MIT
"""Audit-Log fuer zustandsaendernde Aktionen ueber die Konsole.

Vorbild, gemessen vor dem Bau statt geraten: `ellmos-controlcenter-mcp`
0.5.1s `gateway-audit.jsonl` (`.AI/.MCP/ellmos-controlcenter-mcp/src/gateway.ts`,
`appendGatewayAuditEntry`). Uebernommen, mit Begruendung je Abweichung:

  - **Ort ausserhalb OneDrive, im Nutzerprofil.** Vorbild:
    `os.homedir()/.ellmos/controlcenter/gateway-audit.jsonl`. Hier analog:
    `~/.ellmos/unified-gui/audit.jsonl` -- ein Log ist Betriebsdatum, kein
    Repo-/Sync-Inhalt (dieselbe Trennung wie `~/.rinnsal/`, `~/.usmc/`).
  - **Env-Override + `off`-Abschaltung**, gleiches Namensschema: Vorbild
    `ELLMOS_GATEWAY_AUDIT_LOG`, hier `UNIFIED_GUI_AUDIT_LOG` (passt zum
    bestehenden `ENV_PREFIX` dieses Repos, siehe config.py).
  - **Argumentnamen, nie Argumentwerte; Groessen, nie Inhalte.** Wortgleiches
    Prinzip aus dem Vorbild-Docstring ("Argument names only. Values are never
    written to the audit log.") -- hier: nur die Top-Level-Schluessel des
    JSON-Bodys, nie deren Werte. Keine Response-Inhalte, nur der Status-Code.
  - **Jede Anfrage wird geloggt, auch eine abgelehnte** ("Jeder Aufruf, auch
    ein abgelehnter, wird als eine JSON-Zeile angehaengt", README_de.md des
    Vorbilds) -- hier: jede schreibende HTTP-Methode, unabhaengig vom
    Ergebnis (2xx/403/4xx/5xx werden alle geschrieben, siehe `_outcome`).

Bewusste Abweichungen vom Vorbild, benannt statt stillschweigend uebernommen:

  - **Keine Rotation.** Im Vorbild-Quellcode selbst nicht vorhanden (geprueft,
    nicht angenommen) -- eine unbegrenzt wachsende JSONL-Datei ist also der
    tatsaechliche Stand des Vorbilds, keine Vereinfachung dieser Portierung.
  - **Kein `_REQUIRED`-Fail-closed-Modus.** Das Vorbild kann per
    `ELLMOS_GATEWAY_AUDIT_REQUIRED=1` einen fehlgeschlagenen Audit-Schreib-
    vorgang zum abgelehnten Aufruf machen. Hier bewusst NICHT gebaut: eine
    interaktive Mensch-GUI-Aktion (P5-Regel aendern, P11-Skill anlegen) soll
    nicht an einem Logging-Bug scheitern -- Audit ist hier immer best-effort,
    nie blockierend. Als Erweiterung benennbar, falls gewuenscht, nicht Teil
    dieses Pakets.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ENV_AUDIT_LOG = "UNIFIED_GUI_AUDIT_LOG"
DEFAULT_AUDIT_LOG = Path.home() / ".ellmos" / "unified-gui" / "audit.jsonl"


def resolve_audit_log_path(override: str | Path | None = None) -> str:
    """Reihenfolge wie das Vorbild: expliziter Parameter > Env-Var > Default."""
    if override is not None:
        return str(override)
    env = os.environ.get(ENV_AUDIT_LOG)
    if env:
        return env
    return str(DEFAULT_AUDIT_LOG)


def is_audit_disabled(path: str) -> bool:
    return path.strip().lower() == "off"


def append_audit_entry(entry: dict[str, Any], audit_log_path: str | Path | None = None) -> tuple[str, str | None]:
    """Haengt `entry` als eine JSON-Zeile an. Gibt (status, error) zurueck --
    status in "written"|"disabled"|"failed", gleiche drei Zustaende wie das
    Vorbilds `GatewayAuditStatus`. Wirft NIE (derselbe Vertrag wie
    `BaseAdapter.probe()` in diesem Repo -- ein Logging-Fehler darf die
    aufrufende Aktion nicht mitreissen)."""
    path = resolve_audit_log_path(audit_log_path)
    if is_audit_disabled(path):
        return "disabled", None
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return "written", None
    except OSError as exc:
        return "failed", str(exc)
