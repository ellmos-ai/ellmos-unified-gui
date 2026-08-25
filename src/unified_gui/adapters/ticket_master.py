# SPDX-License-Identifier: MIT
"""ticket-master-Adapter: Ticket-Dateisystem + Score-/Routing-Vorschau.

Wahrheit bleibt dateibasiert (T-*.txt, Multi-Host-Claim per Dateiname) —
der Adapter liest/schreibt genau dieses Format und laesst die Claim-Konvention
unangetastet (DECISIONS.md D06). Score-Formel und Tier-Schwellen stammen aus
ticket-master (prompts/TICKET-MASTER.md + config/ticket-master.config.json).
"""
from __future__ import annotations

import json
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import TicketMasterConfig
from .base import AdapterError, BaseAdapter

# Kategorien v1 (verbindlich seit 2026-07-31, ticket-master docs/CATEGORIES.de.md):
# 8 Cluster + 2 rueckwaertskompatible Legacy-Ordner (lesbar, keine neuen Eintraege
# laut Doku). "INBOX" deckt zwei physische Quellen ab: lose T-*.txt-Dateien direkt
# im Root (dokumentierter Alias von INBOX) und der echte INBOX/-Unterordner.
# "OPEN" war nie ein echter Ordnername -- ticket-master fuehrt es selbst nur als
# Legacy-Clustername (lib/ticket_writer.py _LEGACY_LIFECYCLE_CLUSTERS).
# T-20260825-608373032: die alte Vor-v1-Liste ("OPEN", "QUEUED", "PENDING",
# "SOLVED", ".USER") machte 129 reale Tickets in ACTIONABLE/BLOCKED/WAITING/
# USER/PARKED/INBOX im P8-Panel unsichtbar.
LIFECYCLE_QUEUES = ("INBOX", "ACTIONABLE", "QUEUED", "BLOCKED", "WAITING", "USER", "PARKED", "SOLVED")
LEGACY_QUEUES = ("PENDING", ".USER")
QUEUES = LIFECYCLE_QUEUES + LEGACY_QUEUES
# Gemirrort aus ticket-masters kanonischem TICKET_FILENAME_RE
# (lib/ticket_writer.py) -- SEMANTISCH aequivalent, nicht Zeichen-identisch:
# ticket-master nutzt benannte Gruppen (date/number/slug/suffix), dieser
# Adapter behaelt aus Kompatibilitaetsgruenden seine eigenen 2 positionalen
# Gruppen (1=kanonische ID "T-DATE-NUMBER", 2=Suffix/Claim) -- der Slug wird
# absichtlich NICHT-capturing mitgelesen und verworfen (er ist nie Teil der
# ID, siehe ticket-master-Kommentar dort). Ein direkter Import von
# ticket-master waere ein neuer Laufzeit-Dependency auf ein anderes
# Plan-D-Modul fuer eine reine Dateinamens-Regex -- deshalb Spiegelung statt
# Import, wie schon bei LIFECYCLE_QUEUES/LEGACY_QUEUES oben.
#
# T-20260825-870761420: die alte Fassung ohne Slug-Gruppe verschluckte jedes
# "T-DATE-NN_beschreibung.txt"-Ticket (SOLVED zeigte 320 statt real ~417,
# PENDING 2 statt 4) -- Drift-Waechter dafuer in
# tests/test_ticket_master_adapter.py.
_TICKET_RE = re.compile(
    r"^(T-\d{8}-\d+)(?:_[A-Za-z0-9][\w-]*)?(?:\.([A-Za-z0-9_-]+))?\.txt$"
)

# Fallback-Schwellen (Score 0-50) — Quelle: ticket-master.config.example.json
DEFAULT_THRESHOLDS = {"tier1_max": 8, "tier2_max": 12, "tier3_max": 28, "tier4_min": 29}
DEFAULT_ADVISOR_THRESHOLD = 35

TICKET_TEMPLATE = """==============================================================
TICKET
==============================================================
ID:            {ticket_id}
TITLE:         {title}
CREATED:       {created}
STATUS:        INBOX
PRIORITY:      {priority}

--------------------------------------------------------------
PROJECT ASSIGNMENT
--------------------------------------------------------------
PIPELINE:      {pipeline}
PROJECT_DIR:   {project}
CONTROL_FILE:  n/a
DOMAIN:        n/a
ENDPOINT:      n/a
URGENCY:       {urgency}

--------------------------------------------------------------
PROBLEM DESCRIPTION
--------------------------------------------------------------
{description}

--------------------------------------------------------------
VERLAUF
--------------------------------------------------------------
{created} Erfasst via Unified GUI (P8 Intake).

--------------------------------------------------------------
LOESUNG
--------------------------------------------------------------
(offen)
"""


@dataclass
class TicketInfo:
    id: str
    title: str
    queue: str
    priority: str
    claimed_by: str | None
    path: str
    created: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "queue": self.queue,
            "priority": self.priority,
            "claimed_by": self.claimed_by,
            "path": self.path,
            "created": self.created,
        }


@dataclass
class RoutingSuggestion:
    score: int
    tier: int
    provider: str
    model: str | None
    advisor: bool
    candidates: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "tier": self.tier,
            "provider": self.provider,
            "model": self.model,
            "advisor": self.advisor,
            "candidates": self.candidates,
        }


class TicketMasterAdapter(BaseAdapter):
    name = "ticket-master"
    label = "ticket-master (Tickets & Routing)"

    def __init__(self, config: TicketMasterConfig | None = None) -> None:
        self.config = config or TicketMasterConfig()
        self.host = socket.gethostname().upper()

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _root(self) -> Path | None:
        if not self.config.tickets_root:
            return None
        root = Path(self.config.tickets_root).expanduser()
        return root if root.is_dir() else None

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            if self._root() is not None:
                caps.add(Capability.TICKETS_RW)
            # Routing-Editor nur, wenn der Config-Ordner existiert (Schreibpfad)
            if self.config.config_dir and Path(self.config.config_dir).expanduser().is_dir():
                caps.add(Capability.ROUTING_CONFIG)
        except Exception:  # noqa: BLE001 — probe wirft nie
            pass
        return caps

    def health(self) -> HealthInfo:
        root = self._root()
        if root is None:
            return HealthInfo("offline", "tickets_root nicht konfiguriert oder nicht vorhanden")
        detail = f"{root}"
        if not self._tm_config():
            detail += " (ohne ticket-master.config.json: Fallback-Tiers)"
            return HealthInfo("degraded", detail)
        return HealthInfo("ok", detail)

    # ------------------------------------------------------------------
    # TicketStore
    # ------------------------------------------------------------------
    def queues(self) -> dict[str, list[dict]]:
        root = self._require_root()
        result: dict[str, list[dict]] = {q: [] for q in QUEUES}
        # INBOX = unclaimed/claimed Tickets direkt im Root (dokumentierter Alias)
        # PLUS der echte INBOX/-Unterordner, gescannt im Loop unten wie jeder
        # andere Cluster.
        for path in sorted(root.glob("T-*.txt")):
            info = self._parse(path, "INBOX")
            if info:
                result["INBOX"].append(info.as_dict())
        for queue in QUEUES:
            folder = root / queue
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("T-*.txt")):
                info = self._parse(path, queue)
                if info:
                    result[queue].append(info.as_dict())
        return result

    def intake(self, title: str, description: str, priority: str = "medium",
               urgency: str = "woche", project: str = "n/a", pipeline: str = "n/a") -> dict:
        title = title.strip()
        if not title:
            raise AdapterError("empty_title", "TITLE ist Pflicht")
        root = self._require_root()
        now = datetime.now()
        ticket_id = self._next_id(root, now)
        content = TICKET_TEMPLATE.format(
            ticket_id=ticket_id,
            title=title,
            created=now.strftime("%Y-%m-%d"),
            priority=priority if priority in ("low", "medium", "high", "critical") else "medium",
            pipeline=pipeline.strip() or "n/a",
            project=project.strip() or "n/a",
            urgency=urgency if urgency in ("sofort", "heute", "woche", "backlog") else "woche",
            description=description.strip() or "(keine Beschreibung)",
        )
        path = root / f"{ticket_id}.txt"
        path.write_text(content, encoding="utf-8")
        info = self._parse(path, "INBOX")
        return info.as_dict() if info else {"id": ticket_id, "path": str(path)}

    def move(self, ticket_id: str, queue: str) -> dict:
        queue = queue.strip().upper()
        if queue not in LIFECYCLE_QUEUES:
            raise AdapterError("invalid_queue", f"{queue} (erlaubt: {', '.join(LIFECYCLE_QUEUES)})")
        root = self._require_root()
        source = self._find(root, ticket_id)
        if source is None:
            raise AdapterError("ticket_not_found", ticket_id)
        target_dir = root if queue == "INBOX" else root / queue
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        if source.resolve() == target.resolve():
            info = self._parse(source, queue)
            return info.as_dict() if info else {}
        source.replace(target)
        info = self._parse(target, queue)
        return info.as_dict() if info else {}

    # ------------------------------------------------------------------
    # Routing-Vorschau (Score -> Tier -> Provider)
    # ------------------------------------------------------------------
    def score_preview(self, clarity: int, complexity: int, creativity: int,
                      context: int, criticality: int) -> RoutingSuggestion:
        values = {"clarity": clarity, "complexity": complexity, "creativity": creativity,
                  "context": context, "criticality": criticality}
        for label, value in values.items():
            if not 0 <= int(value) <= 10:
                raise AdapterError("invalid_score_input", f"{label} muss 0-10 sein")
        # Formel aus ticket-master: (10-Klarheit)+Komplexitaet+Kreativitaet+Kontext+Kritikalitaet
        score = (10 - int(clarity)) + int(complexity) + int(creativity) + int(context) + int(criticality)

        tm_config = self._tm_config() or {}
        thresholds = {**DEFAULT_THRESHOLDS, **(tm_config.get("score_thresholds") or {})}
        if score <= int(thresholds["tier1_max"]):
            tier = 1
        elif score <= int(thresholds["tier2_max"]):
            tier = 2
        elif score <= int(thresholds["tier3_max"]):
            tier = 3
        else:
            tier = 4

        providers = tm_config.get("providers") or {}
        default_provider = tm_config.get("default_provider") or (next(iter(providers), "claude"))
        provider_cfg = providers.get(default_provider) or {}
        advisor_cfg = tm_config.get("advisor") or {}
        advisor_threshold = int(advisor_cfg.get("threshold_score", DEFAULT_ADVISOR_THRESHOLD))

        return RoutingSuggestion(
            score=score,
            tier=tier,
            provider=default_provider,
            model=provider_cfg.get("default_model"),
            advisor=bool(score >= advisor_threshold),
            candidates=list(providers.keys()) or ["claude", "codex", "agy"],
        )

    # ------------------------------------------------------------------
    # intern
    # ------------------------------------------------------------------
    def _require_root(self) -> Path:
        root = self._root()
        if root is None:
            raise AdapterError("no_tickets_root", "tickets_root nicht konfiguriert/vorhanden")
        return root

    def _tm_config(self) -> dict | None:
        if not self.config.config_dir:
            return None
        path = Path(self.config.config_dir).expanduser() / "ticket-master.config.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # RoutingConfig (P4): Score-Tiers, default_provider, router_command, advisor
    # ------------------------------------------------------------------
    def routing_config(self) -> dict:
        """Aktive Routing-Parameter (Config oder Fallback-Defaults)."""
        tm_config = self._tm_config() or {}
        return {
            "config_exists": self._tm_config() is not None,
            "config_dir": self.config.config_dir,
            "score_thresholds": {**DEFAULT_THRESHOLDS, **(tm_config.get("score_thresholds") or {})},
            "default_provider": tm_config.get("default_provider", "claude"),
            "providers": list((tm_config.get("providers") or {}).keys()) or ["claude", "codex", "agy"],
            "router_command": tm_config.get("router_command"),
            "advisor": {**{"enabled": False, "model": "opus",
                           "threshold_score": DEFAULT_ADVISOR_THRESHOLD},
                        **(tm_config.get("advisor") or {})},
        }

    def set_routing_config(self, updates: dict) -> dict:
        """Schreibt Routing-Parameter in ticket-master.config.json.

        Existiert nur die .example-Datei, wird daraus die echte Config erzeugt
        (Konvention von ticket-master: example kopieren und anpassen)."""
        if not self.config.config_dir:
            raise AdapterError("no_config_dir", "config_dir nicht konfiguriert")
        config_dir = Path(self.config.config_dir).expanduser()
        if not config_dir.is_dir():
            raise AdapterError("config_dir_missing", str(config_dir))
        path = config_dir / "ticket-master.config.json"
        current = self._tm_config()
        if current is None:
            example = config_dir / "ticket-master.config.example.json"
            if example.is_file():
                try:
                    current = json.loads(example.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    current = {}
            else:
                current = {}

        allowed = {"score_thresholds", "default_provider", "router_command", "advisor"}
        for key, value in updates.items():
            if key not in allowed:
                raise AdapterError("field_not_editable", key)
            if key in ("score_thresholds", "advisor") and isinstance(value, dict):
                merged = dict(current.get(key) or {})
                merged.update(value)
                current[key] = merged
            else:
                current[key] = value

        thresholds = {**DEFAULT_THRESHOLDS, **(current.get("score_thresholds") or {})}
        if not (int(thresholds["tier1_max"]) < int(thresholds["tier2_max"])
                < int(thresholds["tier3_max"]) < int(thresholds["tier4_min"])):
            raise AdapterError("invalid_thresholds",
                               "tier1_max < tier2_max < tier3_max < tier4_min erforderlich")

        path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        return self.routing_config()

    def _next_id(self, root: Path, now: datetime) -> str:
        datestr = now.strftime("%Y%m%d")
        highest = 0
        for path in root.rglob(f"T-{datestr}-*.txt"):
            match = _TICKET_RE.match(path.name)
            if match:
                try:
                    highest = max(highest, int(match.group(1).rsplit("-", 1)[1]))
                except ValueError:
                    continue
        return f"T-{datestr}-{highest + 1:02d}"

    def _find(self, root: Path, ticket_id: str) -> Path | None:
        candidates = [root] + [root / q for q in QUEUES]
        for folder in candidates:
            if not folder.is_dir():
                continue
            for path in folder.glob(f"{ticket_id}*.txt"):
                match = _TICKET_RE.match(path.name)
                if match and match.group(1) == ticket_id:
                    return path
        return None

    def _parse(self, path: Path, queue: str) -> TicketInfo | None:
        match = _TICKET_RE.match(path.name)
        if not match:
            return None
        title, priority, created = "", "", ""
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:2000]
            for line in head.splitlines():
                upper = line.strip().upper()
                if upper.startswith("TITLE:"):
                    title = line.split(":", 1)[1].strip()
                elif upper.startswith("PRIORITY:"):
                    priority = line.split(":", 1)[1].strip()
                elif upper.startswith("CREATED:"):
                    created = line.split(":", 1)[1].strip()
        except OSError:
            pass
        return TicketInfo(
            id=match.group(1),
            title=title or path.stem,
            queue=queue,
            priority=priority or "-",
            claimed_by=match.group(2),
            path=str(path),
            created=created,
        )
