# Changelog — ellmos Unified GUI

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
