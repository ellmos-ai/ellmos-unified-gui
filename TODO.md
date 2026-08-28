# TODO — ellmos Unified GUI

**Stand:** 2026-08-26 · Phasen aus KONZEPT.md §7. `[ ]` offen · `[~]` in Arbeit · `[x]` fertig

## STATUS

| Category | Status | Evidence / next gate |
|---|---|---|
| Core console | DONE | Fourteen capability-driven web panels; the suite collects 203 tests. |
| Packaging and security | DONE | Pinned private CI, security policy, build and metadata regression are present. |
| Homebase adapter | BLOCKED | Requires a canonical `hb_route_*` seam or a verified taskplan-backed state seam. |
| BACH integration | WAITING | Requires the separate BACH repository write gate to be open. |
| Public release | USER | Repository history/privacy choice and explicit visibility approval remain owner gates. |

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
- [x] **P14 Governance** (2026-08-26): rein lesender Consumer für den fertigen
      Markdown-Vertrag `controlcenter_list_governance`. Das Panel zeigt Quellenstatus,
      Teilständigkeit, Decision-Staleness und valides BYUM-Count 0 unverändert an;
      es liest keine Quelldatei, föderiert nichts selbst und bietet weder Übernahme
      noch Ausführung an. Neue Capability `governance.ro`; 9 neue Vertrags-/Paneltests,
      einschließlich Degradierung bei einem veralteten gebauten MCP-Bundle.
- [x] Adapter `skills_catalog` (Subprozess-Wrapper um `catalog.py`, skills-Repo)
      + **P11 Skill-Wizard** (2026-08-18): Gerüst anlegen (`catalog.py create`), das bisher als
      `{{Beschreibung der Faehigkeit}}`-Platzhalter stehenbleibende
      `description:`-Pflichtfeld ausfüllen (Read-Modify-Write mit
      Rundlauf-Beweis über `catalog.py`s eigenen `parse_frontmatter()`,
      nicht nur "die Datei enthält meinen String"), statische S-Tests
      (`--type static`, kein LLM-Aufruf). Bewusste Grenze: der eigentliche
      Skill-Körper (Anweisungen) + Testfälle/Subagent-Evals/
      Beschreibungs-Optimierung bleiben Aufgabe der konversationellen
      `skill-creator`-Skill — kein halbfertiger Nachbau ihrer Eval-Schleife.
      Rollen-Gating wie P5/P2 (admin bei Host-Session). 21 neue Tests
      (`test_skills_catalog_adapter.py`, `test_p11_skill_wizard.py`),
      Vollsuite 107 -> 128/128 grün. Real-E2E-Beweis gegen den echten
      skills-Klon (Wegwerf-Kategorie `_wizard-smoke-test`, danach entfernt):
      create+describe+quality liefen gegen echte Daten, Score 5.0/Exzellent.

## Phase 4 — Konsolidierung

- [ ] **P13: persistenter Chat-Source-of-Truth — NO_OP/BLOCKED (Shadow-Befund
      2026-08-28):** Der Adapter konstruiert `ChatRuntime` ohne expliziten Store;
      der aktuelle Modulvertrag fällt dadurch auf `SQLiteChatStore(":memory:")`
      zurück. Zugleich akzeptiert P13 eine frei vom Client gesetzte `chat_id`, obwohl
      `ellmos-chat` Authentifizierung und Besitzbindung ausdrücklich an den Host
      delegiert. Vor einer persistenten Aktivierung muss der Host nicht erratbare Chat-IDs an
      den authentifizierten Nutzer oder Raum binden. Das Zielschema muss Nutzer-/Raum-,
      Modell- und Zeitstempelsemantik erhalten; Fehlerpersistenz, Reset/Löschung,
      Kontextkomprimierung, genau ein Writer, Datenbankkopie-Migration und Rollback
      benötigen gemeinsame Vertragstests. Bis ein kanonischer `ellmos-chat`-Plan-D-Klon
      mit erreichbarem Remote und Commit-Pin existiert, bleibt dies ein dokumentiertes
      Migrationsgate und keine Aktivierungsaufgabe.

- [ ] **Adapter `homebase` (hb_route_stats, hb_state_task_*) — BLOCKED, mit konkretem
      Befund (2026-08-19; vormals "sobald Execution-Backends real"):** nachgemessen statt weiter vage
      formuliert. `hb_route_stats` gehört zu `hb_route_*`, das laut
      `ellmos-homebase-mcp/CHANGELOG.md` (Alpha.14, 2026-07-04, seither ohne Folgeeintrag)
      weiterhin explizit "bundled-only (canonical requested, no seam implemented yet)"
      ist — ein Adapter dagegen würde eine disconnected Kopie statt echter
      Routing-Daten zeigen, redundant zum bereits vorhandenen echten `clutch`-Adapter
      (Phase 3). `hb_state_task_*` deklariert zwar seit Alpha.14 einen canonical-Seam
      auf Rinnsals `TaskClient` (`~/.rinnsal/scanner_tasks.db`) — **dieser Pfad
      existiert auf diesem Host nicht** (Rinnsal ist tot, task-master/`taskplan.db`
      ist der reale Nachfolger; der Seam-Fix `hb_state_task_*` → `taskplan.db` ist
      noch nicht verifiziert). Ein Adapter heute würde also
      bundled/stale Daten zeigen. Präzise Vorbedingung für den Bau: entweder ein
      `hb_route_*`-canonical-Seam entsteht in homebase-mcp, oder der taskplan-Seam landet
      UND wird hier verifiziert (Import-Test gegen echte `taskplan.db`) — beides liegt
      ausserhalb dieses Repos, kein Nebenbei-Schritt.

- [ ] **BACH mountet Unified GUI; überlappende BACH-Panels deprecaten — WAITING
      (2026-08-19, dasselbe Ticket): BACH-Repo ist bis ~2026-08-22 read-only/kein
      Push gesperrt** (Judging-Hold, siehe globale Regeln). Der Mount-Teil braucht
      denselben Eingriff wie ellmos-core bekam (`console.py`/`mount_console()`,
      Settings, `pip install .[console]`-Extra) — das ist ein Schreibzugriff auf
      BACHs eigenen Code, also NICHT vor Lock-Aufhebung machbar. Lesen aus BACH
      (z. B. um den Mount-Punkt zu identifizieren) wäre erlaubt gewesen, wurde aber
      bewusst zurückgestellt, bis der Bau selbst wieder möglich ist — ein reiner
      Lese-Vorlauf ohne baldigen Bau hätte keinen Mehrwert. Nach Lock-Aufhebung:
      denselben `console.py`-Ansatz wie in `ellmos-core` spiegeln, dann überlappende
      BACH-eigene Panels (Agenten-Dispatch, Skills, Routinen — soweit BACH eigene
      GUI-Ansichten dafür hat) als deprecated markieren, nicht sofort entfernen.

- [x] **ellmos-core: Operator-Bereich = Unified-GUI-Mount (2026-08-18):** `ellmos-core` mountet diese GUI
      jetzt tatsächlich, nicht mehr nur theoretisch kompatibel. Auf der ellmos-core-Seite:
      neuer `console.py` (`mount_console(app, prefix)`, lazy import + graceful
      degradation, exakt das Muster von `auth_providers.py`/LDAP), neue Settings
      `console_enabled`/`console_prefix` (Default AUS), Aufruf am Ende von `app.py`,
      optionaler Extra `pip install .[console]` in `pyproject.toml` (git-URL, gepinnter
      Commit — wie `clutch-router`). Neuer Cross-Repo-Beweis
      `tests/test_ellmos_core_integration.py` hier im Repo (skip-if-sibling-missing wie
      `test_p5_role_gating.py`): ein ECHTER ellmos-core-Prozess (kein Fake-Adapter) mit
      echtem Login+Session zeigt, dass Rolle `user` bei P5-Schreibpfaden real 403 bekommt
      und Rolle `admin` real durchkommt — plus ein manueller uvicorn-Boot-Smoke (echter
      Prozess auf Port 8811, echte Logins über curl, `/control/` erreichbar, `/chat`
      unverändert funktionsfähig).
      **Bewusst NICHT in diesem Durchgang:** Audit-Log fürs Mounten selbst (separater
      Punkt unten) sowie Installer-/Docker-Verdrahtung.
- [x] Audit-Log für schreibende Aktionen (2026-08-18 — Muster gemessen: `ellmos-controlcenter-mcp`
      0.5.1s `gateway-audit.jsonl`, siehe `audit_log.py`-Docstring für den vollen Vergleich
      inkl. bewusster Abweichungen). Neu: `audit_log.py` (JSONL-Writer,
      `~/.ellmos/unified-gui/audit.jsonl`, Env `UNIFIED_GUI_AUDIT_LOG`, `off` schaltet ab,
      wirft nie) + `audit_middleware.py` (`AuditMiddleware`, loggt jede schreibende
      HTTP-Methode POST/PUT/PATCH/DELETE — dieselbe Menge, die `security._WRITE_METHODS`
      bereits definiert, wiederverwendet statt dupliziert). Registriert in
      `web/app.py::create_app()`, wirkt dadurch automatisch auch im Mount-Betrieb
      (`mount()` ruft `create_app()` intern auf) — deckt ALLE Panels ab, nicht nur die
      drei rollen-gegateten (P2/P5/P11), ohne Panel-für-Panel-Nacharbeit. Nur
      Argumentnamen im Log, nie -werte; nur Status-Code, nie Response-Inhalt. Ein Fehler
      im Audit-Pfad darf die echte Antwort nie verhindern (zwei dedizierte
      Load-bearing-Tests: werfender Auth-Adapter, unschreibbarer Log-Pfad — beide beweisen
      `resp.status_code == 200` bleibt unverändert). 27 neue Tests
      (`test_audit_log.py`, `test_audit_middleware.py`, `test_audit_integration.py` —
      Letzterer mit einem echten E2E-Beweis gegen den realen skills-Klon: P11-Create landet
      real im Audit-Log). Vollsuite 128 -> 155/155 grün. `tests/conftest.py` fixt dabei
      einen selbst gefundenen Bug: ein erster Testlauf schrieb ohne Isolierung echte
      Zeilen in `~/.ellmos/unified-gui/audit.jsonl` — global `UNIFIED_GUI_AUDIT_LOG=off`
      für die Testsuite ergänzt.
- [x] **README-Sprachen, Release als `ellmos-ai/unified-gui` (MIT) geprüft (2026-08-19,
      dasselbe Ticket, Restpaket 3).** Befund: `README_de.md` war seit längerem
      inhaltlich reicher als `README.md` (80 vs. 53 Zeilen) — drei Abschnitte fehlten
      im Englischen komplett (Panels-Zielbild, Multi-System/Cloud-Konfiguration,
      Verwandte Module) und die Statuszeile war auf beiden Seiten stale (v0.7.0/
      11 Panels/155 Tests statt real v0.8.0/12 Panels/170 Tests) — dasselbe
      Stale-Doku-Muster wie zuvor in diesem Ticket schon mehrfach gefunden. Beide
      Dateien jetzt auf 1:1-Parität + aktuellen Stand gebracht (siehe P-006
      Sprachstufen-Policy). MIT-Lizenz bereits korrekt gesetzt: `LICENSE`-Datei
      vorhanden, `pyproject.toml` `license = {text = "MIT"}`. **Beobachtung, NICHT
      umgesetzt:** kein Repo in diesem Ökosystem (auch nicht `agent-launcher`,
      `skills`, `ellmos-core`) nutzt Git-Tags/GitHub-Releases — "Release ... prüfen"
      war daher als Verifikation gelesen, nicht als neue Tagging-Konvention (hätte
      sonst einen Parallelstandard erzeugt). Getrennt davon: `VISIBILITY-POLICY.md`s
      Grundsatz "Werkzeug-Module bleiben öffentlich" würde für dieses generische
      Konsolen-Tool eigentlich sprechen — Sichtbarkeit bewusst NICHT geändert
      (PRIVATE bleibt PRIVATE bis zu einer expliziten Entscheidung, siehe
      `repo-publish-check`-Skill für den Prüfweg, falls das später ansteht).

## Offen / zu klären

- [x] **Auth-Seam-Design im Mount-Betrieb — P5 als erstes Panel angebunden
      (2026-08-18):**
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
