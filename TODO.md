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

## Phase 2 — BACH-Anbindung (Agenten, Tasks, Routinen)  ✅ (2026-07-11; Routine-Bindings s. Offen)

- [x] Adapter `bach` (CLI-JSON: `agent --json`, `task`, REST: `/api/daemon/*`,
      `/api/prompt-library`)
- [x] **P2 Agenten**: Liste + Start/Stop/Steer/Checkpoint, permission_mode/Modellwahl
- [x] **P7 Tasks**: Aggregation BACH + `~/.rinnsal/scanner_tasks.db` (+ homebase),
      Provenienz-Badges, Zuweisung (assign) an Agent/Modell
- [x] **P6 Routinen**: Jobs/Chains CRUD gegen BACH-Daemon-API; Routine-Bindings
      (Modell + Rollen-Prompt + Skills, Validierung via SkillIndex)
- [x] **P1 Prompts**: BACH-prompt-library-Adapter + profiprompt-v1-Export +
      PromptBoard-Import (Referenz: BACH `/api/prompt-library`)
- [x] Mount-Test: Einbettung in BACH `gui/server.py` unter `/control` (live, alle 6 Panels nach Re-Probe)

## Phase 3 — Modelle, Routing, Skills  ✅ (2026-07-11; homebase → Phase 4)

- [x] Adapter `ollama` (/api/tags, /api/ps, /api/version) — `api_models` entfiel:
      clutch IST die Modell-/Credential-Registry (`clutch keys`, getriebe.json) [D07]
- [x] Adapter `clutch` (models/stats/route via CLI-JSON) — `homebase` auf Phase 4
      verschoben (Routing/Tasks dort noch Dry-run-Stubs, Nutzen aktuell gering)
- [x] **P3 Modelle**: clutch-Gears + Ollama-Live-Sicht (Tags, geladene Modelle);
      Hinzufügen/Default-je-Rolle bleibt clutch-Config (getriebe.json)
- [x] **P4 Routing**: ticket-master-Score/Tiers/default_provider/router_command/
      Advisor-Editor (legt Config aus .example an) + clutch-Stats & Route-Vorschau
- [x] Adapter `controlcenter` (eigener minimaler stdio-MCP-Client, mcp_client.py)
      + **P9 Skills** (Inventar 109 Skills, Intent-Matching, Bundles)

## Phase 4 — Konsolidierung

- [ ] Adapter `homebase` (hb_route_stats, hb_state_task_*) sobald Execution-Backends real

- [ ] BACH mountet Unified GUI; überlappende BACH-Panels deprecaten
- [ ] ellmos-core: Operator-Bereich = Unified-GUI-Mount (Abgrenzung Endnutzer/Operator)
- [ ] Audit-Log für schreibende Aktionen (Muster ellmos-core)
- [ ] README-Sprachen, Release als `ellmos-ai/unified-gui` (MIT) prüfen

## Offen / zu klären

- [ ] Auth-Seam-Design im Mount-Betrieb (BACH-GUI hat kein Login; ellmos-core RBAC)
- [ ] Watcher-Koexistenz: P5 gegen live :8095 vs. eingebettete permissions.py-Nutzung
      bei nicht laufendem Daemon (Fallback-Reihenfolge)
- [ ] Schreibpfad Routine-Bindings in BACH (Job-Argumente vs. eigene Metadaten-Tabelle)
