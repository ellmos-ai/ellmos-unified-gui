# TODO — ellmos Unified GUI

**Stand:** 2026-07-11 · Phasen aus KONZEPT.md §7. `[ ]` offen · `[~]` in Arbeit · `[x]` fertig

## TASKPLAN v0.3 — Anpassung noetig [C 2026-07-14]

> **Nichts bricht, nichts crasht.** Die GUI liest 9 Spalten explizit per Name
> (`adapters/scanner_tasks.py:74-75`, `sqlite3.Row`) — die 8 neuen Spalten sind fuer
> sie schadlos unsichtbar. Geschrieben wird ohnehin nur ueber den Wrapper-CLI, und der
> ist bereits nachgezogen.
>
> **ABER: Ein Anzeigefehler ist scharf, sobald zum ersten Mal echt delegiert wird.**

**Was sich geaendert hat:** `agent_id` trug frueher DREI Bedeutungen (Anleger,
Bearbeiter, Rolle) und wurde beim Zuweisen ueberschrieben — die Herkunft ging dabei
verloren. Seit TASKPLAN 0.3 sind sie getrennt: `created_by` (unveraenderlich, der
Anleger) und `assigned_to` + `delegation_status` (der Bearbeiter). `assign()` schreibt
nur noch in Letztere.

- [ ] **(hoch) Zuweisungs-Anzeige korrigieren — zeigt sonst den Falschen.**
      `src/unified_gui/adapters/scanner_tasks.py:92` mappt heute:
      ```python
      "assigned_to": row["agent_id"] if row["agent_id"] != "default" else "",
      ```
      `agent_id` ist ab jetzt der **Anleger**, nicht der Bearbeiter. Verschaerfend:
      die SELECT-Liste in `:74` endet bei `updated_at` — `assigned_to` und `created_by`
      werden **gar nicht erst geholt**. Die GUI ist fuer die neuen Spalten also
      *strukturell blind*, nicht bloss falsch gemappt.

      **Fix beruehrt ZWEI Stellen:**
      1. `:74` — `assigned_to`, `created_by`, `delegation_status`, `effort`, `scope`
         mitselektieren.
      2. `:92` — auf `row["assigned_to"]` mappen; Fallback auf `agent_id` nur, solange
         `assigned_to` leer ist (Altbestand: alle 38 Tasks haben heute ein leeres
         `assigned_to`).

      **Warum es heute noch nicht auffaellt:** Der alte Wrapper ueberschrieb `agent_id`
      beim Zuweisen — die Anzeige sah dadurch *zufaellig* richtig aus. Ab der ersten
      echten `assign()`-Nutzung zeigt die GUI dauerhaft den Anleger statt des
      Bearbeiters.
      *Aufwand: easy · Scope: local*

- [ ] **(mittel) Neue Felder anzeigen:** `effort` (easy/medium/large/special) und
      `scope` (local/central) bestimmen, ob eine Aufgabe autonom bearbeitet werden darf.
      **Uneingestufte Aufgaben (`effort` leer) fasst der TASKSOLVER nicht an** — sie
      sind faktisch unsichtbar. Eine Spalte oder ein Filter dafuer macht sofort
      sichtbar, warum eine Aufgabe liegen bleibt. Ebenso nuetzlich: `project_path` /
      `root_id` (in welchem Projekt liegt sie?).
      *Aufwand: easy · Scope: local*

- [ ] **(mittel) DB-Pfad aus der TASKPLAN-Konfiguration lesen statt hartzukodieren.**
      `config.py:45` (`DISCOVERY_DEFAULTS`) und `_control-center/unified-gui.config.json`
      setzen beide fest `~/.rinnsal/scanner_tasks.db`. `~/.taskplan/taskplan.toml`
      (`[storage] path`) wird **nicht** gelesen.
      **Heute folgenlos** (beide zeigen auf dieselbe DB), aber ein latentes Drift-Risiko:
      Wird die TOML kuenftig umgestellt, zieht die GUI nicht mit und liest still die
      falsche Datenbank — ohne Fehler, ohne Warnung.
      Loesung: `from taskplan.client import get_default_db_path` (mit Fallback auf den
      bisherigen Default, falls taskplan nicht importierbar ist).
      *Aufwand: easy · Scope: local*

- [ ] **(niedrig) Pfad in der eigenen CLAUDE.md korrigieren:** Sie nennt noch
      `.MODULES/ellmos-unified-gui`; das Modul liegt unter `.MODULES/.RUNTIME/`.
      *Aufwand: easy · Scope: local*

**Nicht betroffen:** `ellmos-homebase-mcp` reicht das Row-Dict unveraendert durch
(`modules/state.py:331-334`) und erbt das neue Schema automatisch ueber den
rinnsal→taskplan-Seam. Dort ist **kein** Fix noetig.

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
