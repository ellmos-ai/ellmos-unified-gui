# TODO — ellmos Unified GUI

**Stand:** 2026-07-11 · Phasen aus KONZEPT.md §7. `[ ]` offen · `[~]` in Arbeit · `[x]` fertig

## Phase 0 — Vorarbeiten (extern)

- [x] BACH-GUI an BACHs Prompt-DB angeschlossen (`/prompt-library` + PromptBoard-Import,
      BACH v3.13.0-bluesky) — Referenz-Implementierung für P1-Adapter `bach`
- [x] Konzeptdokumente + Ordnergrundstruktur dieses Moduls (2026-07-11)

## Phase 1 — Fundament + größte Lücken  ✅ (2026-07-11)

- [x] `pyproject.toml` + Paketskelett (`unified_gui.create_app()` / `mount()`)
- [x] Web-Shell: FastAPI-Router, Jinja2/HTMX-Grundgerüst, Nav aus Panel-Registry
- [x] Capability-Registry + `BaseAdapter` (probe/health, Timeout-fest, gecacht)
- [x] Adapter `lock_master` (permissions.py-Einbindung + Watcher-REST :8095)
- [x] **P5 Berechtigungen**: Regel-Editor für `LOCK.permissions.json`
      (allow/deny/ask, Patterns, applies_to_agents) + Lock-Übersicht + Bulk-Lockdown
- [x] Adapter `ticket_master` (tickets/-Dateisystem, config/*.json, Score-Preview)
- [x] **P8 Tickets**: Intake-Formular, Router-Vorschau (Score→Provider-Kandidaten),
      Queue-Board (PENDING/QUEUED/SOLVED), Claim-Anzeige
- [x] Standalone-Guard (localhost + Origin-Check wie lock-master-Watcher)
- [x] Smoke-Tests: probe-Degradierung (Backend fehlt ⇒ Panel weg, kein Crash)

## Phase 2 — BACH-Anbindung (Agenten, Tasks, Routinen)

- [ ] Adapter `bach` (CLI-JSON: `agent --json`, `task`, REST: `/api/daemon/*`,
      `/api/prompt-library`)
- [ ] **P2 Agenten**: Liste + Start/Stop/Steer/Checkpoint, permission_mode/Modellwahl
- [ ] **P7 Tasks**: Aggregation BACH + `~/.rinnsal/scanner_tasks.db` (+ homebase),
      Provenienz-Badges, Zuweisung (assign) an Agent/Modell
- [ ] **P6 Routinen**: Jobs/Chains CRUD gegen BACH-Daemon-API; Routine-Bindings
      (Modell + Rollen-Prompt + Skills, Validierung via SkillIndex)
- [ ] **P1 Prompts**: BACH-prompt-library-Adapter + profiprompt-v1-Export +
      PromptBoard-Import (Referenz: BACH `/api/prompt-library`)
- [ ] Mount-Test: Einbettung in BACH `gui/server.py` unter `/control`

## Phase 3 — Modelle, Routing, Skills

- [ ] Adapter `ollama` (/api/tags, Verfügbarkeit) + `api_models`
      (proprietäre Modelle via Credential-Referenz, NIE Klartext-Keys)
- [ ] Adapter `clutch` (Provider/Routing) + `homebase` (hb_route_stats, hb_state_task)
- [ ] **P3 Modelle**: lokale + API-Modelle, Hinzufügen, Health-Check, Default je Rolle
- [ ] **P4 Routing**: ticket-master-Score/Tiers editieren, router_command, Advisor,
      Statistik (hb_route_stats)
- [ ] Adapter `controlcenter` + **P9 Skills** (Inventar, Intent-Matching)

## Phase 4 — Konsolidierung

- [ ] BACH mountet Unified GUI; überlappende BACH-Panels deprecaten
- [ ] ellmos-core: Operator-Bereich = Unified-GUI-Mount (Abgrenzung Endnutzer/Operator)
- [ ] Audit-Log für schreibende Aktionen (Muster ellmos-core)
- [ ] README-Sprachen, Release als `ellmos-ai/unified-gui` (MIT) prüfen

## Offen / zu klären

- [ ] Auth-Seam-Design im Mount-Betrieb (BACH-GUI hat kein Login; ellmos-core RBAC)
- [ ] Watcher-Koexistenz: P5 gegen live :8095 vs. eingebettete permissions.py-Nutzung
      bei nicht laufendem Daemon (Fallback-Reihenfolge)
- [ ] Schreibpfad Routine-Bindings in BACH (Job-Argumente vs. eigene Metadaten-Tabelle)
