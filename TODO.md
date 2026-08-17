# TODO — ellmos Unified GUI

**Stand:** 2026-07-11 · Phasen aus KONZEPT.md §7. `[ ]` offen · `[~]` in Arbeit · `[x]` fertig

## TASKPLAN v0.3 — Anpassung  ✅ (2026-07-14, TASKSOLVER; Tasks 40/41/42)

Hintergrund: `agent_id` trug früher DREI Bedeutungen (Anleger, Bearbeiter, Rolle)
und wurde beim Zuweisen überschrieben. Seit TASKPLAN 0.3 sind `created_by` (Anleger)
und `assigned_to` (Bearbeiter) getrennt. Begründungen: **DECISIONS.md [D09]**.

- [x] **(hoch) Zuweisungs-Anzeige korrigiert** — P7 zeigte den Anleger statt des
      Bearbeiters. Die SELECT-Liste holte die neuen Spalten gar nicht erst (strukturell
      blind), und `agent_id` wurde auf `assigned_to` gemappt. **Der in dieser Liste
      ursprünglich vorgeschlagene Fallback `assigned_to or agent_id` hätte den Bug
      reproduziert**: `agent_id` trägt bei nicht zugewiesenen Tasks den Anleger
      (`scanner`) — empirisch 25 von 44 Tasks. Der Rückfall prüft jetzt den Anleger
      mit. [D09]
- [x] **(mittel) `effort`/`scope`/`project_path`/`root_id` werden angezeigt** —
      uneingestufte Aufgaben (leeres `effort`) bekommen einen Warn-Chip. Sie sind der
      Normalfall, nicht die Ausnahme: **38 von 44 Tasks** sind uneingestuft und werden
      von den Loops nicht angefasst. Genau das war vorher unsichtbar.
- [x] **(mittel) DB-Pfad kommt aus der TASKPLAN-Konfiguration** (`taskplan.toml`,
      `[storage] path`) — in `config.py` und in der geteilten
      `_control-center/unified-gui.config.json`, wo der explizite Wert jede Auflösung
      überstimmte. **Nicht** `get_default_db_path()` wie hier vorgeschlagen: das fällt
      auf die leere `~/.taskplan/taskplan.db` zurück. [D09]
- [x] **(niedrig) Pfad in der eigenen CLAUDE.md korrigiert** (`.MODULES/.RUNTIME/`).

**Nicht betroffen:** `ellmos-homebase-mcp` reicht das Row-Dict unverändert durch
(`modules/state.py:331-334`) und erbt das neue Schema automatisch über den
rinnsal→taskplan-Seam. Dort ist **kein** Fix nötig.

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

- [x] **Auth-Seam-Design im Mount-Betrieb — P5 als erstes Panel angebunden
      (2026-08-18, Sovereign-Programm-Ticket T-20260816-361197589, Stufe 2 Rest):**
      neuer `HostAuthAdapter` (`adapters/host_auth.py`, Capability `AUTH_ROLE`) liest
      die eingeloggte Person + Rolle aus `ellmos_core.web.get_current_user(request)`,
      wenn die GUI unter ellmos-core gemountet ist (lazy import, degradiert auf `None`
      wenn kein Host/keine Session — kein neuer Zwang wo bisher keiner war, kein
      zweites Login, `ellmos-core` bleibt alleinige Quelle der Wahrheit fuer Rollen).
      In P5 gaten Schreibpfade (`add_rule`/`remove_rule`/`set_default`/`bulk-lock`/
      `bulk-unlock`) jetzt auf Rolle `admin`, wenn eine Host-Session vorliegt; Lesepfade
      bleiben offen. 16 neue Tests (`test_host_auth_adapter.py`,
      `test_p5_role_gating.py`), Vollsuite weiterhin gruen (97/97).
      **Fortgesetzt 2026-08-18 (vierter Durchgang, Nutzer-Prioritaetsansage
      "Systemaufgaben zuerst"):** P2 (Agenten) nach demselben Muster angebunden —
      `build(adapter, auth_adapter=None)` gaten `start`/`stop`/`steer`/`clear-steer`/
      `checkpoint` jetzt auf Rolle `admin`, wenn eine Host-Session vorliegt; Entscheidung
      war hier eindeutig (Agenten starten/stoppen/steuern ist die staerkere Aktion,
      laufende Compute-Kosten + moegliche Stoerung fremder Sitzungen). `list_agents`
      bleibt offen. P2 hatte zuvor GAR KEINE eigene Testsuite — 6 neue Tests
      (`test_p2_role_gating.py`) decken jetzt zusaetzlich zum Gating erstmals ab, dass
      die Schreibpfade den Adapter ueberhaupt korrekt aufrufen. Vollsuite 97 → **103/103
      gruen**.
      **P9 (Skills) GEMESSEN, bewusst NICHT angebunden — echter Befund, kein
      Zeitmangel:** `p9_skills.py` hat drei Endpunkte (`GET /skills`, `POST /find`,
      `GET /bundles`), **alle drei sind lesend/abfragend** — `find` ist ein POST nur
      wegen des Anfrage-Bodys (Intent-String), keine Mutation. Es gibt schlicht keinen
      Schreibpfad, den man auf `admin` gaten koennte. Eine Rollen-Sichtbarkeit auf
      Skill-Ebene (nur bestimmte Rollen sehen bestimmte Skills) waere KEINE Anbindung
      eines bestehenden Backends, sondern eine neue Zugriffskontrollschicht, die
      `ellmos-controlcenter-mcp` heute nicht kennt — das waere Neubau statt
      Wiederverwendung und damit bewusst NICHT in diesem Durchgang begonnen.
- [ ] Watcher-Koexistenz: P5 gegen live :8095 vs. eingebettete permissions.py-Nutzung
      bei nicht laufendem Daemon (Fallback-Reihenfolge)
- [ ] Schreibpfad Routine-Bindings in BACH (Job-Argumente vs. eigene Metadaten-Tabelle)
