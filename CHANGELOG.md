# Changelog — ellmos Unified GUI

## [Unreleased] (TASKPLAN v0.3)

### Added

- **P12 Races: read-only compare-race-Reportbrowser (2026-08-19, Sovereign-Programm-Ticket
  T-20260816-361197589, Rest-Paket 2a):** neuer `CompareRaceAdapter` +
  Panel `p12_races` zeigen echte, bereits gelaufene Races (`PROMPT.md`/`RACE.md`/`RUN-*.md`,
  inkl. modellmanuellem Judge-Urteil, falls ausgefüllt) — Auto-Discovery findet auf diesem
  Host real 18 Races. Bewusst NUR lesend: `run`/`record`/`olympiade` bleiben aussen vor,
  weil ein "Race starten"-Knopf in einem Web-Panel echte Mehrmodell-API-Kosten auslösen
  würde und wer den Judge stellt eine Produktentscheidung ist, keine Verdrahtungsfrage
  (Messung dazu: `SOVEREIGN_ZUSAMMENBINDEN_2026-08-18.md`). `read_race_dir()` wird per
  echtem Paket-Import aus dem konfigurierten compare-race-Klon genutzt (kein Re-Implement).
  Neue Capability `races.ro`. 15 neue Tests (8 Adapter, 7 Panel-E2E), Vollsuite 155 → 170/170
  grün. KnowledgeDigest-Teil desselben Restpakets bewusst NICHT gebaut — echte
  Produktentscheidung nötig (Detail im Ticket-VERLAUF). Version 0.7.0 → 0.8.0.
  Nebenbefund korrigiert: `src/unified_gui/__init__.py`s `__version__` stand auf 0.5.0
  (zwei Restpaket-Versionsbumps in pyproject.toml nicht nachgezogen) — jetzt wieder
  synchron.
- **Audit-Log für schreibende Aktionen (2026-08-18, Sovereign-Programm-Ticket
  T-20260816-361197589, Rest-Paket 2c):** neue `audit_log.py` (append-only JSONL,
  `~/.ellmos/unified-gui/audit.jsonl`, Env `UNIFIED_GUI_AUDIT_LOG`, `off` schaltet ab) +
  `audit_middleware.py` (`AuditMiddleware`, loggt jede POST/PUT/PATCH/DELETE-Anfrage —
  wer/Rolle, was/Panel+Aktion, wann, Ergebnis, Dauer, nur Argument**namen** nie -werte).
  Vorbild `ellmos-controlcenter-mcp` 0.5.1s `gateway-audit.jsonl`, gemessen vor dem Bau
  (Ort/Format/PII-Disziplin übernommen; keine Rotation, kein Fail-closed-Modus — beide
  bewusst nicht Teil des Vorbilds bzw. dieses Pakets, siehe Modul-Docstring). In
  `create_app()` registriert, wirkt dadurch auch im `mount()`-Betrieb und deckt jeden
  Panel-Schreibpfad ab, nicht nur die drei bereits rollen-gegateten (P2/P5/P11). Ein
  Fehler im Audit-Pfad selbst kann eine echte Konsolen-Aktion nie verhindern (zwei
  Load-bearing-Tests dafür). 27 neue Tests, Vollsuite 128 -> 155/155 grün; echter E2E-Beweis
  gegen den realen skills-Klon (P11-Create landet real im Log).
- **P11 Skill-Wizard (2026-08-18, Sovereign-Programm-Ticket
  T-20260816-361197589, Stufe 3 "Skillgenerator mit Wizard"):** neuer
  `SkillsCatalogAdapter` (`adapters/skills_catalog.py`, Subprozess-Wrapper um
  `catalog.py` im kanonischen skills-Klon) + neue Capability `SKILLS_CREATE`.
  Schließt Ampel-Zeile 6 (gelb -> grün, siehe
  `sovereign-private/_reports/SOVEREIGN_AMPEL_RECHECK_2026-08-17.md`): bisher
  gab es nur read-only Inventar (P9), keinen GUI-Weg für eine echte
  Skill-Neuanlage. Der Wizard schließt den strukturierten Teil — Gerüst
  anlegen, das `description:`-Pflichtfeld ausfüllen (die CLI ließ es bisher
  als `{{Beschreibung der Faehigkeit}}`-Platzhalter stehen), statische
  S-Tests (`--type static`) — und lässt den Skill-Körper bewusst der
  konversationellen `skill-creator`-Skill (Interview, Testfälle,
  Subagent-Evals, Beschreibungs-Optimierung braucht ein LLM in der Schleife,
  kein zustandsloses Panel kann das nachbauen; siehe Modul-Docstrings für die
  genaue Grenze). Rollen-Gating wie P5/P2. 21 neue Tests, Vollsuite
  107 -> 128/128 grün; Real-E2E-Beweis gegen den echten skills-Klon
  (Wegwerf-Kategorie, danach entfernt).

- **Real gemountet in ellmos-core, nicht nur kompatibel (Sovereign-Programm-Ticket
  T-20260816-361197589, Stufe 4 "zusammenbinden"):** `ellmos-core` mountet diese
  Konsole jetzt tatsächlich (neues `console.py`/`console_enabled` dort, Extra
  `pip install .[console]`). Neuer Cross-Repo-Test
  `tests/test_ellmos_core_integration.py`: ein echter ellmos-core-Prozess (kein
  Fake-Auth-Double) beweist, dass Login+Rolle real auf P5-Schreibpfade wirken
  (`user`→403, `admin`→durch). Vollsuite 103 → 107/107 grün.
- **P5 Rollen-Gating im Mount-Betrieb (Sovereign-Programm-Ticket
  T-20260816-361197589, Stufe 2):** neuer `HostAuthAdapter`
  (`adapters/host_auth.py`, Capability `AUTH_ROLE`) liest, wenn die GUI unter
  `ellmos-core` gemountet ist, die eingeloggte Person + Rolle aus
  `ellmos_core.web.get_current_user(request)` — lazy import, degradiert auf
  `None` ohne Host/Session (Standalone, BACH-Mount: unverändertes Verhalten,
  kein zweites Login, `ellmos-core` bleibt einzige Quelle der Wahrheit für
  Rollen). P5s Schreibpfade (Regeln ändern, Default setzen, Bulk-Lock/-Unlock)
  verlangen jetzt Rolle `admin`, wenn eine Host-Session vorliegt; Lesepfade
  bleiben offen. 16 neue Tests, Vollsuite 97/97 grün.
- **P2 Rollen-Gating, gleiches Muster (Stufe 2, vierter Durchgang):** `start`/
  `stop`/`steer`/`clear-steer`/`checkpoint` verlangen jetzt ebenfalls Rolle
  `admin` bei vorliegender Host-Session (`list_agents` bleibt offen). P2 hatte
  zuvor keine eigene Testsuite — 6 neue Tests (`test_p2_role_gating.py`)
  decken zusätzlich zum Gating erstmals den Adapter-Aufrufpfad ab. Vollsuite
  97 → 103/103 grün. **P9 (Skills) geprüft und bewusst nicht angebunden:**
  alle drei Endpunkte sind lesend/abfragend, es gibt keinen Schreibpfad zum
  Gaten — siehe `TODO.md` für den vollständigen Befund.

### Documentation

- **Statuszeile in `README.md`/`README_de.md`/`llms.txt` war seit der Erstanlage
  (2026-07-11, „Phase 1, v0.1.0, nur P5+P8") eingefroren, obwohl seither P1-P4,
  P6, P7, P9 (Phase 2/3, 2026-07-11) und P10 (2026-08-07, [D11]) dazukamen —
  gemessen im Rahmen des Sovereign-Ampel-Re-Checks (Ticket T-20260816-361197589):
  `src/unified_gui/panels/` enthält 10 Panel-Module, `tests/` läuft 85/85 grün.
  Statuszeile auf den gemessenen Stand korrigiert (10 Panels, v0.4.0+, Phase 4
  offen). `KONZEPT.md` war bereits korrekt (P10 dort schon dokumentiert) und
  blieb unverändert.

### Fixed

- **P5/lock-master-Adapter lud nach der lock-master-Stack-Zerlegung (2026-07-26)
  nur noch die leere Shim-Hülle.** `permissions.py` ist dort seit der Zerlegung
  ein selbstersetzender Shim (setzt das reale Modul unter `sys.modules[<Name>]`);
  der Adapter behielt seine lokale Modulvariable und fand `load_permissions`
  nicht mehr. Jetzt wird nach `exec_module` das ersetzte Modul aus `sys.modules`
  übernommen (+ fehlender `sys`-Import). 3 rote Adapter-Tests wieder grün (85/85).

- **P7-Taskliste gegen Attribut-Injection gehärtet.** Taskwerte aus Scanner-
  und BACH-Backends werden nicht mehr als zusammengesetztes `innerHTML`
  gerendert: DOM-Text, Tooltip-Property und Event-Listener halten selbst
  Anführungszeichen in `project_path` als Daten statt als Attribute oder Code.
- **P7 zeigte den Anleger als Bearbeiter.** Der Scanner-Adapter mappte `agent_id`
  auf `assigned_to`; seit TASKPLAN 0.3 ist `agent_id` aber der Anleger. Zudem holte
  die SELECT-Liste die neuen Spalten gar nicht erst — die GUI war für sie
  strukturell blind. Jetzt gilt `assigned_to`; ein Rückfall auf `agent_id` greift
  nur bei Altbestand und nie, wenn dort ein Anleger steht (`scanner`/`default`/
  `created_by`). Ohne diese Unterscheidung hätten 25 der 44 Tasks den Anleger als
  Bearbeiter angezeigt. [D09]
- Alte, noch nicht auf v0.3 migrierte Queues brechen den Adapter nicht mehr: Er
  liest strikt read-only und kann nie selbst migrieren, wählt die Spalten deshalb
  nach `PRAGMA table_info` und zeigt notfalls weniger, statt mit `no such column`
  auszufallen. [D09]

### Added

- **START.bat** — installationsfreier Start aus jedem Checkout und jeder
  Plan-D-Deploykopie (`src/` via `%~dp0` auf dem PYTHONPATH, Default-Port 8990).
- **Plan-D-Migration (2026-08-13, D-20260808-005):** privates Repo
  `ellmos-ai/unified-gui`, kanonischer Klon `C:\_Local_DEV\repos\unified-gui`,
  OneDrive-Ordner ist `.git`-lose Quell-/Deploykopie mit Pointer
  `unified-gui.repo.md`.

### Changed

- **DB-Pfad folgt der TASKPLAN-Konfiguration** (`~/.taskplan/taskplan.toml`,
  `[storage] path`) statt hartkodiert zu sein — in `config.py` UND in der geteilten
  `_control-center/unified-gui.config.json` (dort überstimmte der explizite Wert
  jede Auflösung). Fallback bleibt `~/.rinnsal/scanner_tasks.db`. [D09]

### Added

- P7 zeigt `effort`, `scope`, `project_path`/`root_id`. Aufgaben ohne `effort`
  bekommen einen Warn-Chip „uneingestuft": Die autonomen Loops fassen sie nicht an —
  im Bestand betrifft das 38 von 44 Tasks, was vorher unsichtbar war.


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
