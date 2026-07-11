# SPDX-License-Identifier: MIT
"""Konfiguration der Unified GUI.

Quellen (spaeter gewinnt): eingebaute Defaults < JSON-Config-Datei < Env-Variablen
< explizit uebergebenes dict. Keine Klartext-Secrets — nur Pfade/URLs/Referenzen.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ENV_PREFIX = "UNIFIED_GUI_"
CONFIG_FILENAME = "unified-gui.config.json"


@dataclass
class LockMasterConfig:
    # Pfad zum lock-master-Repo (fuer permissions.py-Import). None => Auto-Discovery.
    module_path: str | None = None
    # Projekt-Roots fuer LOCK.permissions.json. Entweder direkte Liste ...
    roots: list[str] = field(default_factory=list)
    # ... oder lock_roots.json (Format des lock-master/_scripts-Systems).
    roots_file: str | None = None
    watcher_url: str = "http://127.0.0.1:8095"
    timeout_s: float = 1.5


@dataclass
class BachConfig:
    # BACH-Repo-Root (Ordner mit system/bach.py) ODER direkt der system/-Ordner.
    bach_root: str | None = None
    # BACH-GUI-Server (Scheduler/Tasks/Prompts via REST).
    rest_url: str = "http://127.0.0.1:8000"
    rest_timeout_s: float = 1.5
    # CLI-Aufrufe (Agenten) dauern wegen BACH-Startup-Hooks Sekunden.
    cli_timeout_s: float = 120.0
    python_exe: str | None = None


@dataclass
class ScannerTasksConfig:
    # Rinnsal-Queue des Hintergrund-Scanners (ausserhalb OneDrive).
    db_path: str | None = None
    # Kanonisches CLI fuer assign/done (scanner_tasks.py).
    tool_path: str | None = None
    python_exe: str | None = None


@dataclass
class ClutchConfig:
    # clutch-Repo (Ordner mit clutch/cli.py) — CLI laeuft mit cwd=Repo.
    repo_path: str | None = None
    python_exe: str | None = None
    timeout_s: float = 45.0


@dataclass
class OllamaConfig:
    url: str = "http://127.0.0.1:11434"
    timeout_s: float = 1.5


@dataclass
class ControlCenterConfig:
    # ellmos-controlcenter-mcp-Repo (mit gebautem dist/index.js).
    repo_path: str | None = None
    node_exe: str = "node"
    timeout_s: float = 30.0


@dataclass
class TicketMasterConfig:
    # Verzeichnis mit T-*.txt + QUEUED/PENDING/SOLVED (live: _control-center/_TICKETS
    # oder ein ticket-master tickets/-Ordner).
    tickets_root: str | None = None
    # Ordner mit ticket-master.config.json (Provider/Score-Tiers); optional.
    config_dir: str | None = None


@dataclass
class UnifiedGuiConfig:
    title: str = "Unified GUI"
    lock_master: LockMasterConfig = field(default_factory=LockMasterConfig)
    ticket_master: TicketMasterConfig = field(default_factory=TicketMasterConfig)
    bach: BachConfig = field(default_factory=BachConfig)
    scanner_tasks: ScannerTasksConfig = field(default_factory=ScannerTasksConfig)
    clutch: ClutchConfig = field(default_factory=ClutchConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    controlcenter: ControlCenterConfig = field(default_factory=ControlCenterConfig)
    # Standalone-Guard: nur lokale Origins/Clients (im Mount-Betrieb Sache des Hosts)
    local_only: bool = True

    @classmethod
    def load(cls, overrides: dict | None = None, config_file: str | Path | None = None) -> "UnifiedGuiConfig":
        data: dict = {}

        path = Path(config_file) if config_file else _default_config_path()
        if path and path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}

        _apply_env(data)
        if overrides:
            _deep_update(data, overrides)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "UnifiedGuiConfig":
        lm = data.get("lock_master") or {}
        tm = data.get("ticket_master") or {}
        bc = data.get("bach") or {}
        sc = data.get("scanner_tasks") or {}
        return cls(
            title=data.get("title", "Unified GUI"),
            local_only=bool(data.get("local_only", True)),
            lock_master=LockMasterConfig(
                module_path=lm.get("module_path"),
                roots=list(lm.get("roots") or []),
                roots_file=lm.get("roots_file"),
                watcher_url=lm.get("watcher_url", "http://127.0.0.1:8095"),
                timeout_s=float(lm.get("timeout_s", 1.5)),
            ),
            ticket_master=TicketMasterConfig(
                tickets_root=tm.get("tickets_root"),
                config_dir=tm.get("config_dir"),
            ),
            bach=BachConfig(
                bach_root=bc.get("bach_root"),
                rest_url=bc.get("rest_url", "http://127.0.0.1:8000"),
                rest_timeout_s=float(bc.get("rest_timeout_s", 1.5)),
                cli_timeout_s=float(bc.get("cli_timeout_s", 120.0)),
                python_exe=bc.get("python_exe"),
            ),
            scanner_tasks=ScannerTasksConfig(
                db_path=sc.get("db_path"),
                tool_path=sc.get("tool_path"),
                python_exe=sc.get("python_exe"),
            ),
            clutch=ClutchConfig(
                repo_path=(data.get("clutch") or {}).get("repo_path"),
                python_exe=(data.get("clutch") or {}).get("python_exe"),
                timeout_s=float((data.get("clutch") or {}).get("timeout_s", 45.0)),
            ),
            ollama=OllamaConfig(
                url=(data.get("ollama") or {}).get("url", "http://127.0.0.1:11434"),
                timeout_s=float((data.get("ollama") or {}).get("timeout_s", 1.5)),
            ),
            controlcenter=ControlCenterConfig(
                repo_path=(data.get("controlcenter") or {}).get("repo_path"),
                node_exe=(data.get("controlcenter") or {}).get("node_exe", "node"),
                timeout_s=float((data.get("controlcenter") or {}).get("timeout_s", 30.0)),
            ),
        )


def _default_config_path() -> Path | None:
    env = os.environ.get(ENV_PREFIX + "CONFIG")
    if env:
        return Path(env).expanduser()
    home = Path.home() / ".unified_gui" / CONFIG_FILENAME
    if home.is_file():
        return home
    return Path.cwd() / CONFIG_FILENAME


def _apply_env(data: dict) -> None:
    """Ausgewaehlte Env-Overrides (flach, dokumentiert im README)."""
    mapping = {
        ENV_PREFIX + "TICKETS_ROOT": ("ticket_master", "tickets_root"),
        ENV_PREFIX + "TM_CONFIG_DIR": ("ticket_master", "config_dir"),
        ENV_PREFIX + "LOCK_MODULE": ("lock_master", "module_path"),
        ENV_PREFIX + "LOCK_ROOTS_FILE": ("lock_master", "roots_file"),
        ENV_PREFIX + "WATCHER_URL": ("lock_master", "watcher_url"),
        ENV_PREFIX + "BACH_ROOT": ("bach", "bach_root"),
        ENV_PREFIX + "BACH_URL": ("bach", "rest_url"),
        ENV_PREFIX + "SCANNER_DB": ("scanner_tasks", "db_path"),
        ENV_PREFIX + "SCANNER_TOOL": ("scanner_tasks", "tool_path"),
    }
    for env_name, (section, key) in mapping.items():
        value = os.environ.get(env_name)
        if value:
            data.setdefault(section, {})[key] = value


def _deep_update(base: dict, extra: dict) -> None:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
