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
