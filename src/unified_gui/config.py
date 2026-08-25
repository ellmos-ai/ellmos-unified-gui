# SPDX-License-Identifier: MIT
"""Konfiguration der Unified GUI — cloud-/multi-system-faehig.

Config-Kaskade (spaeter gewinnt, alle Dateien optional):
  1. Shared-Basis   ~/OneDrive/.TOPICS/_control-center/unified-gui.config.json
  2. Shared-Host    ~/OneDrive/.TOPICS/_control-center/unified-gui.config.<HOST>.json
  3. User-Basis     ~/.unified_gui/unified-gui.config.json
  4. User-Host      ~/.unified_gui/unified-gui.config.<HOST>.json
  5. cwd (Dev)      ./unified-gui.config.json
  6. Env-Variablen  UNIFIED_GUI_*
  7. overrides-dict (create_app(config={...}))

Ist UNIFIED_GUI_CONFIG gesetzt, ersetzt diese EINE Datei die Quellen 1-5
(exklusiv — fuer Tests und Sonderfaelle).

Portabilitaet: Alle Pfadfelder expandieren `~`, `$VAR` und `%VAR%` — Configs
gehoeren deshalb in `~`-Notation geschrieben, damit dieselbe Datei auf
WORKSTATION (lukas), LAPTOP (User) und Mac funktioniert. Fehlen Felder,
ergaenzt eine Auto-Discovery die Standard-Layout-Pfade des Oekosystems
(abschaltbar: "discovery": false bzw. UNIFIED_GUI_DISCOVERY=0).
Keine Klartext-Secrets — nur Pfade/URLs/Referenzen.
"""
from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

ENV_PREFIX = "UNIFIED_GUI_"
CONFIG_FILENAME = "unified-gui.config.json"
SHARED_CONFIG_DIR = "~/OneDrive/.TOPICS/_control-center"

# Altpfad der Task-Queue (Rinnsal-Erbe). Bleibt der Rueckfall, wenn TASKPLAN
# nichts konfiguriert hat oder gar nicht installiert ist.
SCANNER_DB_FALLBACK = "~/.rinnsal/scanner_tasks.db"


def scanner_db_default() -> str:
    """DB-Pfad der Task-Queue — die TASKPLAN-Konfiguration schlaegt den Altpfad.

    Reihenfolge wie bei TASKPLAN (TASKPLAN_DB > [storage] path > RINNSAL_DB),
    damit GUI und TASKPLAN nicht auseinanderlaufen: Wird die TOML umgestellt,
    zieht die GUI mit, statt still die falsche Datenbank zu lesen.

    Bewusst NICHT `taskplan.client.get_default_db_path()`: dessen letzter Schritt
    faellt auf ~/.taskplan/taskplan.db zurueck — im Bestand eine LEERE DB — und
    legt dabei auch noch das Verzeichnis an. Die GUI wuerde dann ohne Fehler und
    ohne Warnung eine leere Queue anzeigen. Fehlt eine Konfiguration, bleibt sie
    deshalb bei ihrem bewaehrten Altpfad.
    """
    env_path = os.environ.get("TASKPLAN_DB", "")
    if env_path:
        return env_path
    try:
        from taskplan.client import configured_db_path
        configured = configured_db_path()
    except Exception:  # noqa: BLE001 — TASKPLAN fehlt/kaputt: Altpfad genuegt
        configured = ""
    return configured or os.environ.get("RINNSAL_DB", "") or SCANNER_DB_FALLBACK


# Standard-Layout dieses Oekosystems (Discovery-Defaults; probe() filtert
# ohnehin alles, was auf einem System nicht existiert). Callables werden erst
# beim Laden ausgewertet — ein Literal wuerde beim Import einfrieren.
DISCOVERY_DEFAULTS = {
    ("lock_master", "module_id"): "lock-master",
    ("lock_master", "module_path"): "~/OneDrive/.TOPICS/.AI/.MODULES/lock-master",
    ("lock_master", "roots_file"): "~/OneDrive/_scripts/lock_roots.json",
    ("ticket_master", "module_id"): "ticket-master",
    ("ticket_master", "tickets_root"): "~/OneDrive/.TOPICS/_control-center/_TICKETS",
    ("ticket_master", "config_dir"): "~/OneDrive/.TOPICS/.AI/.MODULES/ticket-master/config",
    ("bach", "bach_root"): "~/OneDrive/.TOPICS/.AI/.OS/BACH",
    ("scanner_tasks", "db_path"): scanner_db_default,
    ("scanner_tasks", "tool_path"): "~/OneDrive/.TOPICS/_control-center/_tasks/_tool/scanner_tasks.py",
    ("clutch", "module_id"): "clutch",
    ("clutch", "repo_path"): "~/OneDrive/.TOPICS/.AI/.MODULES/clutch",
    ("controlcenter", "repo_path"): "~/OneDrive/.TOPICS/.AI/.MCP/ellmos-controlcenter-mcp",
    ("skills_catalog", "repo_path"): lambda: _first_existing_file(SKILLS_CATALOG_CANDIDATES, "catalog.py"),
    ("decisions", "index_path"):
        "~/OneDrive/.TOPICS/_control-center/_DECISIONS/_tools/decisions.index.json",
    ("decisions", "chain_dir"): "~/OneDrive/.TOPICS/_control-center/_DECISIONS",
    ("decisions", "clicker_path"): lambda: _first_existing(DECISION_CLICKER_CANDIDATES),
    ("compare_race", "repo_path"): lambda: _first_existing_file(COMPARE_RACE_CANDIDATES, "src/compare_race/report.py"),
    ("compare_race", "races_dir"): lambda: _compare_race_races_dir(),
    # Wheelhouse M1 (T-20260825-835413946): ellmos-chat-Staging-Modul
    # (kein pip-Paket, keine .git -- Konsum ueber sys.path, siehe
    # adapters/ellmos_chat.py).
    ("ellmos_chat", "module_path"): "~/OneDrive/.TOPICS/.AI/.MODULES/.RUNTIME/ellmos-chat",
}

# decision-clicker liegt nach Plan D im lokalen Klon, NICHT in OneDrive — der
# Pfad ist deshalb nicht ~-relativ und je System verschieden. probe() filtert
# ohnehin, was nicht existiert.
DECISION_CLICKER_CANDIDATES = (
    "C:/_Local_DEV/repos/decision-clicker",
    "~/_Local_DEV/repos/decision-clicker",
    "~/repos/decision-clicker",
    "~/decision-clicker",
)


def _first_existing(candidates: tuple[str, ...]) -> str | None:
    for value in candidates:
        path = Path(_expand(value))
        if (path / "src" / "decision_clicker").is_dir():
            return str(path)
    return None


# Die kanonische skills-Bibliothek liegt ebenfalls nach Plan D lokal (nicht
# OneDrive) -- gleicher Grund, gleiches Discovery-Muster wie decision-clicker.
SKILLS_CATALOG_CANDIDATES = (
    "C:/_Local_DEV/repos/skills",
    "~/_Local_DEV/repos/skills",
    "~/repos/skills",
    "~/skills",
)


def _first_existing_file(candidates: tuple[str, ...], filename: str) -> str | None:
    for value in candidates:
        path = Path(_expand(value))
        if (path / filename).is_file():
            return str(path)
    return None


# compare-race liegt ebenfalls nach Plan D lokal (nicht OneDrive) — gleiches
# Discovery-Muster wie skills/decision-clicker.
COMPARE_RACE_CANDIDATES = (
    "C:/_Local_DEV/repos/compare-race",
    "~/_Local_DEV/repos/compare-race",
    "~/repos/compare-race",
    "~/compare-race",
)


def _compare_race_races_dir() -> str | None:
    """Liest races_dir aus compare-races EIGENER Config (~/.compare-race/...) —
    keine Neuerfindung/Kopie des Pfads, sondern dieselbe Quelle, die auch die
    CLI benutzt (`compare_race.config.load()`s HOME_PLACEHOLDER-Logik nachgebildet,
    ohne das Paket importieren zu muessen, falls nur races_dir gebraucht wird)."""
    cfg_path = Path(_expand("~/.compare-race/compare-race.config.json"))
    if not cfg_path.is_file():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    races_dir = data.get("races_dir")
    if not isinstance(races_dir, str) or not races_dir:
        return None
    return races_dir.replace("<HOME>", str(Path.home()))


def _module_catalog_candidates() -> list[Path]:
    configured = os.environ.get("ELLMOS_MODULES_CATALOG")
    one_drive = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE")
    values = [
        configured,
        str(Path(one_drive) / ".TOPICS" / ".AI" / ".MODULES" / "modules.catalog.json") if one_drive else None,
        "~/OneDrive/.TOPICS/.AI/.MODULES/modules.catalog.json",
        "~/.TOPICS/.AI/.MODULES/modules.catalog.json",
    ]
    result: list[Path] = []
    for value in values:
        if not value:
            continue
        candidate = Path(_expand(value)).resolve()
        if candidate not in result:
            result.append(candidate)
    return result


def resolve_module_path(module_id: str | None, fallback: str | None = None, suffix: str | None = None) -> str | None:
    """Löst eine Modul-ID katalog-first auf; ein konfigurierter Altpfad bleibt Fallback."""
    if module_id:
        for catalog_path in _module_catalog_candidates():
            try:
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if catalog.get("schema") != "ellmos.modules-catalog.v1":
                continue
            for module in catalog.get("modules", []):
                if not isinstance(module, dict) or module.get("id") != module_id:
                    continue
                source = module.get("resolved_source")
                if not isinstance(source, str) or not source:
                    break
                path = (catalog_path.parent / source).resolve()
                if suffix:
                    path /= suffix
                if path.exists():
                    return str(path)
                break
    return _expand(fallback)


def _expand(value: str | None) -> str | None:
    """Expandiert ~, $VAR und %VAR% — macht Configs system-portabel."""
    if not value:
        return value
    return os.path.expanduser(os.path.expandvars(str(value)))


def hostname() -> str:
    return socket.gethostname().upper()


@dataclass
class LockMasterConfig:
    module_id: str | None = None
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
    module_id: str | None = None
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
class SkillsCatalogConfig:
    # Klon mit catalog.py (kanonisch C:\_Local_DEV\repos\skills, Plan D --
    # nicht OneDrive, siehe SKILLS_CATALOG_CANDIDATES).
    repo_path: str | None = None
    python_exe: str | None = None
    timeout_s: float = 45.0


@dataclass
class CompareRaceConfig:
    # Klon mit src/compare_race/report.py (Plan D, siehe COMPARE_RACE_CANDIDATES).
    # Nur fuer read_race_dir() (reines Lesen) -- kein Race-Trigger, kein Judge
    # aus der Konsole. Wer den Judge stellt und ob echte LLM-Kosten aus einem
    # Web-Panel ausgeloest werden sollen, ist eine Produktentscheidung.
    repo_path: str | None = None
    # Ordner mit den Race-Unterordnern (PROMPT.md/RACE.md/RUN-*.md); Default
    # kommt aus compare-races EIGENER Config, nicht dupliziert.
    races_dir: str | None = None


@dataclass
class EllmosChatConfig:
    """ellmos-chat als optionaler chat.runtime-Provider (Wheelhouse M1,
    T-20260825-835413946). Staging-Modul (kein pip-Paket) -- module_path
    zeigt auf den Ordner MIT src/ellmos_chat/, Konsum per sys.path-
    Erweiterung analog CompareRaceConfig/repo_path. Keine Klartext-Secrets:
    backend_type/default_model bleiben auf einen lokalen Ollama-Default
    begrenzt (siehe Modul-Docstring oben) -- API-Keys werden hier bewusst
    nicht konfiguriert.
    """
    module_path: str | None = None
    backend_type: str = "ollama"
    default_model: str = "qwen3.6:35b-mlx"
    timeout_s: float = 30.0

@dataclass
class TicketMasterConfig:
    module_id: str | None = None
    # Verzeichnis mit T-*.txt + QUEUED/PENDING/SOLVED (live: _control-center/_TICKETS
    # oder ein ticket-master tickets/-Ordner).
    tickets_root: str | None = None
    # Ordner mit ticket-master.config.json (Provider/Score-Tiers); optional.
    config_dir: str | None = None


@dataclass
class DecisionsConfig:
    module_id: str | None = None
    # Pfad zur generierten decisions.index.json (_control-center/_DECISIONS/_tools).
    # Reicht fuer die reine Lesesicht (DECISIONS_RO).
    index_path: str | None = None
    # Kettenordner (_control-center/_DECISIONS) -- Wurzel der TO-DECIDE-*.txt.
    chain_dir: str | None = None
    # decision-clicker-Repo (Ordner mit src/decision_clicker). Ist es da, kommt
    # DECISIONS_RW dazu: Entscheiden/Einstellen/Postfach laufen ueber dessen
    # Kernlogik. Fehlt es, bleibt P10 exakt wie zuvor read-only. [D11]
    clicker_path: str | None = None


@dataclass
class UnifiedGuiConfig:
    title: str = "Unified GUI"
    lock_master: LockMasterConfig = field(default_factory=LockMasterConfig)
    ticket_master: TicketMasterConfig = field(default_factory=TicketMasterConfig)
    decisions: DecisionsConfig = field(default_factory=DecisionsConfig)
    bach: BachConfig = field(default_factory=BachConfig)
    scanner_tasks: ScannerTasksConfig = field(default_factory=ScannerTasksConfig)
    clutch: ClutchConfig = field(default_factory=ClutchConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    controlcenter: ControlCenterConfig = field(default_factory=ControlCenterConfig)
    skills_catalog: SkillsCatalogConfig = field(default_factory=SkillsCatalogConfig)
    compare_race: CompareRaceConfig = field(default_factory=CompareRaceConfig)
    ellmos_chat: EllmosChatConfig = field(default_factory=EllmosChatConfig)
    # Standalone-Guard: nur lokale Origins/Clients (im Mount-Betrieb Sache des Hosts)
    local_only: bool = True
    # Audit-Log-Zielpfad fuer zustandsaendernde Aktionen; None -> audit_log.py
    # loest selbst auf (Env UNIFIED_GUI_AUDIT_LOG > ~/.ellmos/unified-gui/audit.jsonl).
    # "off" schaltet ab (siehe audit_log.py).
    audit_log_path: str | None = None

    @classmethod
    def load(cls, overrides: dict | None = None, config_file: str | Path | None = None) -> "UnifiedGuiConfig":
        data: dict = {}

        if config_file:
            sources: list[Path] = [Path(_expand(str(config_file)))]
        else:
            sources = _config_sources()
        for path in sources:
            if not path.is_file():
                continue
            try:
                _deep_update(data, json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue

        _apply_env(data)
        if overrides:
            _deep_update(data, overrides)
        _apply_discovery(data)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "UnifiedGuiConfig":
        lm = data.get("lock_master") or {}
        tm = data.get("ticket_master") or {}
        dc = data.get("decisions") or {}
        bc = data.get("bach") or {}
        sc = data.get("scanner_tasks") or {}
        return cls(
            title=data.get("title", "Unified GUI"),
            local_only=bool(data.get("local_only", True)),
            audit_log_path=data.get("audit_log_path"),
            lock_master=LockMasterConfig(
                module_id=lm.get("module_id"),
                module_path=resolve_module_path(lm.get("module_id"), lm.get("module_path")),
                roots=[_expand(r) for r in (lm.get("roots") or [])],
                roots_file=_expand(lm.get("roots_file")),
                watcher_url=lm.get("watcher_url", "http://127.0.0.1:8095"),
                timeout_s=float(lm.get("timeout_s", 1.5)),
            ),
            ticket_master=TicketMasterConfig(
                module_id=tm.get("module_id"),
                tickets_root=_expand(tm.get("tickets_root")),
                config_dir=resolve_module_path(tm.get("module_id"), tm.get("config_dir"), "config"),
            ),
            decisions=DecisionsConfig(
                module_id=dc.get("module_id"),
                index_path=_expand(dc.get("index_path")),
                chain_dir=_expand(dc.get("chain_dir")),
                clicker_path=resolve_module_path(
                    dc.get("module_id") or "decision-clicker", dc.get("clicker_path")),
            ),
            bach=BachConfig(
                bach_root=_expand(bc.get("bach_root")),
                rest_url=bc.get("rest_url", "http://127.0.0.1:8000"),
                rest_timeout_s=float(bc.get("rest_timeout_s", 1.5)),
                cli_timeout_s=float(bc.get("cli_timeout_s", 120.0)),
                python_exe=_expand(bc.get("python_exe")),
            ),
            scanner_tasks=ScannerTasksConfig(
                db_path=_expand(sc.get("db_path")),
                tool_path=_expand(sc.get("tool_path")),
                python_exe=_expand(sc.get("python_exe")),
            ),
            clutch=ClutchConfig(
                module_id=(data.get("clutch") or {}).get("module_id"),
                repo_path=resolve_module_path(
                    (data.get("clutch") or {}).get("module_id"),
                    (data.get("clutch") or {}).get("repo_path"),
                ),
                python_exe=_expand((data.get("clutch") or {}).get("python_exe")),
                timeout_s=float((data.get("clutch") or {}).get("timeout_s", 45.0)),
            ),
            ollama=OllamaConfig(
                url=(data.get("ollama") or {}).get("url", "http://127.0.0.1:11434"),
                timeout_s=float((data.get("ollama") or {}).get("timeout_s", 1.5)),
            ),
            controlcenter=ControlCenterConfig(
                repo_path=_expand((data.get("controlcenter") or {}).get("repo_path")),
                node_exe=(data.get("controlcenter") or {}).get("node_exe", "node"),
                timeout_s=float((data.get("controlcenter") or {}).get("timeout_s", 30.0)),
            ),
            skills_catalog=SkillsCatalogConfig(
                repo_path=_expand((data.get("skills_catalog") or {}).get("repo_path")),
                python_exe=_expand((data.get("skills_catalog") or {}).get("python_exe")),
                timeout_s=float((data.get("skills_catalog") or {}).get("timeout_s", 45.0)),
            ),
            compare_race=CompareRaceConfig(
                repo_path=_expand((data.get("compare_race") or {}).get("repo_path")),
                races_dir=_expand((data.get("compare_race") or {}).get("races_dir")),
            ),
            ellmos_chat=EllmosChatConfig(
                module_path=_expand((data.get("ellmos_chat") or {}).get("module_path")),
                backend_type=(data.get("ellmos_chat") or {}).get("backend_type", "ollama"),
                default_model=(data.get("ellmos_chat") or {}).get("default_model", "qwen3.6:35b-mlx"),
                timeout_s=float((data.get("ellmos_chat") or {}).get("timeout_s", 30.0)),
            ),
        )


def _config_sources() -> list[Path]:
    """Kaskade der Config-Dateien (spaeter in der Liste gewinnt beim Merge).

    UNIFIED_GUI_CONFIG (Env) ersetzt die komplette Kaskade durch genau eine
    Datei — exklusiv, damit Tests/Sonderfaelle hermetisch bleiben."""
    env = os.environ.get(ENV_PREFIX + "CONFIG")
    if env:
        return [Path(_expand(env))]

    host = hostname()
    shared_dir = Path(_expand(SHARED_CONFIG_DIR))
    user_dir = Path.home() / ".unified_gui"
    stem = CONFIG_FILENAME.rsplit(".json", 1)[0]
    return [
        shared_dir / CONFIG_FILENAME,
        shared_dir / f"{stem}.{host}.json",
        user_dir / CONFIG_FILENAME,
        user_dir / f"{stem}.{host}.json",
        Path.cwd() / CONFIG_FILENAME,
    ]


def _apply_discovery(data: dict) -> None:
    """Ergaenzt fehlende Pfadfelder um Standard-Layout-Defaults (~-Notation).

    Nur Felder, die nach allen Quellen noch fehlen; explizite Werte —
    auch explizites null in einer Config/Override — bleiben unangetastet.
    Abschaltbar via "discovery": false oder UNIFIED_GUI_DISCOVERY=0."""
    env_flag = os.environ.get(ENV_PREFIX + "DISCOVERY")
    if env_flag is not None and env_flag.strip().lower() in ("0", "false", "off", "no"):
        return
    if data.get("discovery") is False:
        return
    for (section, key), default in DISCOVERY_DEFAULTS.items():
        block = data.setdefault(section, {})
        if key not in block:
            block[key] = default() if callable(default) else default


def _apply_env(data: dict) -> None:
    """Ausgewaehlte Env-Overrides (flach, dokumentiert im README)."""
    mapping = {
        ENV_PREFIX + "TICKETS_ROOT": ("ticket_master", "tickets_root"),
        ENV_PREFIX + "TM_CONFIG_DIR": ("ticket_master", "config_dir"),
        ENV_PREFIX + "DECISIONS_INDEX": ("decisions", "index_path"),
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
