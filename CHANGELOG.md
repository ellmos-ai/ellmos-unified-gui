# Changelog — ellmos Unified GUI

## [0.4.0] - 2026-07-11 (Multi-System/Cloud)

### Added

- Config-Kaskade: Shared-Basis in OneDrive (_control-center/unified-gui.config.json,
  synct auf alle Systeme) < Shared-Host < ~/.unified_gui (Basis+Host) < cwd <
  Env < Overrides; Host-Overrides via unified-gui.config.<HOSTNAME>.json [D08]
- Pfad-Expansion (~, $VAR, %VAR%) in allen Pfadfeldern — dieselbe Config
  funktioniert auf WORKSTATION (lukas), LAPTOP (User) und Mac
- Auto-Discovery der Standard-Layout-Pfade fuer fehlende Felder
  (discovery=false bzw. UNIFIED_GUI_DISCOVERY=0 schaltet ab; explizites
  null bleibt respektiert); UNIFIED_GUI_CONFIG ersetzt die Kaskade exklusiv
- Control-Center-Start: START-UNIFIED-GUI.bat (Port-Check, PYTHONPATH-
  Fallback, %USERPROFILE%-neutral) + Menue in START.bat; Registrierung in
  controlcenter.stack.json und MANIFEST.md

### Changed

- Maschinen-spezifische Configs (absolute C:/Users/...-Pfade) entfernt —
  ersetzt durch die geteilte ~-notierte Basis in OneDrive


## [0.3.0] - 2026-07-11 (Phase 3)

### Added

- mcp_client.py: minimaler stdio-MCP-Client (JSON-RPC newline-delimited,
  initialize-Handshake, tools/call) — wiederverwendbar fuer weitere MCP-Backends
- Adapter `clutch`: Modell-Registry (13 Gears inkl. Kosten/Staerken), Routing-
  Statistik und Route-Vorschau via CLI-JSON (cwd=Repo); Credentials bleiben in
  clutchs Store — die GUI zeigt nie Schluessel
- Adapter `ollama`: /api/tags, /api/ps, /api/version (Live-Sicht lokale Modelle)
- Adapter `controlcenter`: Skill-Inventar/Intent-Matching/Bundles ueber den
  ellmos-controlcenter-mcp (kurzlebige Node-Sessions)
- ticket-master-Adapter: RoutingConfig-RW — Score-Tiers, default_provider,
  router_command, Advisor editierbar; legt ticket-master.config.json bei Bedarf
  aus der .example an; Schwellen-Validierung
- Panels: P3 Modelle (clutch+Ollama nebeneinander), P4 Routing (Editor +
  clutch-Stats/Route-Vorschau), P9 Skills (Inventar, Intent-Suche)

### Changed

- ROUTING_CONFIG wird nur gemeldet, wenn config_dir existiert (Schreibpfad)
- api_models-Adapter entfiel bewusst: clutch ist die kanonische Modell-/
  Credential-Registry [D07]; homebase-Adapter auf Phase 4 verschoben


## [0.2.0] - 2026-07-11 (Phase 2)

### Added

- Adapter `bach`: REST (Scheduler /api/daemon/*, Tasks, Prompt-Bibliothek) +
  CLI-JSON (Agenten start/stop/steer/clear-steer/checkpoint, Task-Zuweisung);
  extract_json() zieht Payloads aus hook-verrauschter CLI-Ausgabe
- Adapter `scanner-tasks`: Rinnsal-Queue read-only (mode=ro) + assign/done
  ueber das kanonische scanner_tasks.py-CLI
- Panels: P1 Prompts (BACH-Bibliothek + PromptBoard-Import + profiprompt-v1-
  Export), P2 Agenten (Dispatch mit Modell/Modus, available_actions-Buttons),
  P6 Routinen (Jobs+Chains CRUD/Toggle/Run, Daemon-Status), P7 Tasks
  (Multi-Quellen-Aggregation mit Provenienz-Badges, Zuweisung an die Quelle)
- BACH bindet die Unified GUI unter /control ein (weiches Optional in
  gui/server.py + Nav-Link System > Unified GUI); Paket editierbar installiert,
  Config-Discovery via ~/.unified_gui/unified-gui.config.json

### Fixed

- Self-Call-Deadlock im Mount-Betrieb: /api/refresh und /api/status sind sync
  (Threadpool), damit Adapter-Probes den eigenen Host abfragen koennen
- urllib.parse.quote statt nicht existentem urllib.request.quote


## [0.1.0] - 2026-07-11 (Phase 1)

### Added

- Paket `unified_gui` mit `create_app()` (Standalone, Local-Guard) und
  `mount(host_app, prefix)` (Einbettung, prefix-sichere Links via root_path)
- Capability-Registry + `BaseAdapter`-Vertrag (probe wirft nie, Re-Probe zur
  Laufzeit via POST /api/refresh — spaeter gestartete Backends werden sichtbar)
- Adapter `lock-master`: dynamischer Import der echten permissions.py,
  Roots aus Liste oder lock_roots.json, LOCK.permissions.json-Regeln
  (add/remove/default, atomarer Write), evaluate(), Watcher-REST
  (locks/scan/prune/bulk-lock/bulk-unlock, degradiert wenn :8095 offline)
- Adapter `ticket-master`: Queues (OPEN/QUEUED/PENDING/SOLVED/.USER) inkl.
  Multi-Host-Claim-Parsing aus Dateinamen, Intake (Template-kompatible
  T-*.txt), Move, Score-/Routing-Vorschau (Formel + Tier-Schwellen +
  Provider/Advisor aus ticket-master.config.json, Fallback-Defaults)
- Panels: P5 Berechtigungen (Regel-Editor, Test-Bench, Lock-Sektion) und
  P8 Tickets (Intake, Router-Vorschau, Queue-Board) — Jinja2 + Vanilla-JS,
  kein Build-Schritt
- 23 Tests: Degradierung, Refresh, Mount, Adapter-Roundtrips gegen die echte
  lock-master-Engine; hermetisch via tests/conftest.py


## [0.1.0-concept] - 2026-07-11

### Added

- Konzeptdokumente: KONZEPT.md (Problem, Panel-Katalog P1–P9, Übergangspfad),
  ARCHITECTURE.md (Capability-Registry, Mount vs. Standalone, Nicht-Ziele),
  docs/ADAPTER-CONTRACT.md (Capabilities, Domänen-Mixins, Routine-Bindings),
  DECISIONS.md (D01–D06), TODO.md (Phasen 0–4)
- Ordnergrundstruktur: `src/unified_gui/{adapters,panels,web}`, `docs/`, `tests/`,
  `.claude/settings.json`, LICENSE (MIT), VERSION, READMEs (de/en)
- Registry-Eintrag in `.AI/.MODULES/README.md`
