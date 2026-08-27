# ARCHITECTURE — ellmos Unified GUI

**Stand:** 2026-08-26 · **Status:** v0.8.0 plus unveröffentlichte Panels — Schichtenmodell des implementierten Kerns und der offenen Phase-4-Seams.

## Schichtenmodell

```
+--------------------------------------------------------------+
|  HOST (optional)                                             |
|  BACH gui/server.py · ellmos-core · Standalone-Server        |
|  -> unified_gui.mount(app, prefix) ODER unified_gui.create_app()
+--------------------------------------------------------------+
|  WEB-SHELL  src/unified_gui/web/                             |
|  FastAPI-Router + Jinja2/HTMX-Templates + Vanilla-JS          |
|  Kein Build-Schritt. Auth kommt vom Host (Seam) oder          |
|  minimaler eingebauter Guard im Standalone-Betrieb.           |
+--------------------------------------------------------------+
|  PANELS  src/unified_gui/panels/                             |
|  P1 Prompts · P2 Agenten · P3 Modelle · P4 Routing ·          |
|  P5 Berechtigungen · P6 Routinen · P7 Tasks · P8 Tickets ·    |
|  P9 Skills · P10 Entscheidungen · P11 Skill-Wizard ·          |
|  P12 Races · P13 Chat · P14 Governance                       |
|  Jedes Panel: required_capabilities + Router + Fragment       |
+--------------------------------------------------------------+
|  ADAPTER  src/unified_gui/adapters/                          |
|  probe()/health()/Domänen-Methoden je Backend                 |
|  bach · lock_master · ticket_master · scanner_tasks · clutch ·|
|  ollama · controlcenter · decisions · host_auth ·             |
|  skills_catalog · compare_race · ellmos_chat                  |
+--------------------------------------------------------------+
|  BACKENDS (extern, autoritativ)                              |
|  BACH (~/.bach/bach.db via CLI/REST) · LOCK*.txt +            |
|  LOCK.permissions.json · tickets/*.txt · Ollama :11434 ·      |
|  clutch · homebase-mcp (stdio) · controlcenter-mcp (stdio)    |
+--------------------------------------------------------------+
```

## Kernmechanik: Capability-Registry

```python
# Pseudocode des Zielbilds
class Capability(str, Enum):
    PROMPTS_RW, PROMPTS_VERSIONS, AGENT_DISPATCH, AGENT_STEER,
    MODELS_LOCAL, MODELS_API, ROUTING_CONFIG, PERMISSIONS_RW,
    LOCKS_RW, SCHEDULER_RW, TASKS_RO, TASKS_ASSIGN, TICKETS_RW,
    SKILLS_DISCOVERY, GOVERNANCE_RO, SKILLS_CREATE,
    DECISIONS_RO, DECISIONS_RW, AUTH_ROLE, RACES_RO,
    CHAT_RUNTIME = ...

registry = CapabilityRegistry()
for adapter in discover_adapters(config):
    caps = adapter.probe()          # schnell, fehlertolerant, cachebar
    registry.register(adapter, caps)

app.include_router(panel.router)    # nur wenn
    # panel.required_capabilities <= registry.available
```

- `probe()` MUSS in < 2 s antworten und darf nie werfen (Timeout → Backend abwesend).
- Panels können **degradieren**: P7 zeigt Tasks read-only, wenn `TASKS_RO` da ist,
  und blendet Zuweisen-Buttons nur bei `TASKS_ASSIGN` ein.
- Re-Probe per Button und periodisch (konfigurierbar), kein Neustart nötig.

## Einbettung (mount) vs. Standalone

| Aspekt | Standalone `create_app()` | Eingebettet `mount(host_app, prefix)` |
|---|---|---|
| Auth | eingebauter Minimal-Guard (Token/localhost) | Host-Session (z. B. BACH-GUI, ellmos-core-RBAC) |
| Nav | eigene Kopfleiste | Host-Nav, Panels als Unterseiten |
| Static | eigener `/static`-Mount | prefix-sicherer Static-Mount |
| Config | `unified_gui.toml` / Env | Host reicht Config-Objekt durch |

Regel: **kein globaler Zustand auf Modulebene** — alles hängt an der App-Instanz,
sonst bricht Doppel-Mounting (BACH + Standalone parallel).

## Adapter-Vertrag (Kurzfassung)

Voll: `docs/ADAPTER-CONTRACT.md`

```python
class BaseAdapter(Protocol):
    name: str                      # "bach", "lock-master", ...
    def probe(self) -> set[Capability]: ...
    def health(self) -> HealthInfo: ...   # für Status-Leiste
```

Domänen-Mixins (nur implementieren, was das Backend kann):
`PromptStore`, `AgentControl`, `ModelProvider`, `RoutingConfig`,
`PermissionStore`, `LockControl`, `Scheduler`, `TaskSource`, `TicketStore`, `SkillIndex`,
`GovernanceReader`. Der `GovernanceReader` transportiert den fertigen
ControlCenter-MCP-Bericht unverändert; er parst oder föderiert keine Quellen selbst.

## Bewusste Nicht-Ziele

- **Kein eigener Datenstore** für Prompts/Rechte/Tickets/Routinen (Views auf die
  kanonischen Quellen, siehe KONZEPT §3.4). Einzige eigene Persistenz: UI-Preferences.
- **Kein Agent-Execution-Engine.** Dispatch geht immer über ein Backend (BACH,
  später agent-bridge). Die GUI startet nie selbst Prozesse an Backends vorbei.
- **Kein Framework-Frontend** (React/Vue/Build-Pipeline).
- **Kein Auth-Neubau** — Host-Seam; Standalone nur Minimal-Guard (localhost-first,
  wie lock-master-Watcher).

## Sicherheitsleitplanken

- Schreibende Panel-Aktionen prüfen VOR Ausführung `LOCK.permissions.json`
  (lock-master-Adapter) — die GUI unterliegt denselben Regeln wie jeder Agent.
- Origin-Guard wie lock-master-Watcher (nur lokale Origins im Standalone-Betrieb).
- API-Keys für proprietäre Modelle: nur Referenzen auf Credential-Store
  (`C:\_Local_DEV\CREDENTIALS\...` bzw. Host-Secrets), NIE Klartext in Config/Repo.
- Audit: schreibende Aktionen als Append-only-Log (Muster: ellmos-core GDPR-Audit).
