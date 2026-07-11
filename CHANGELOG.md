# Changelog — ellmos Unified GUI

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
