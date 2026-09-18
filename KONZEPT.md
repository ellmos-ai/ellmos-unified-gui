# KONZEPT — ellmos Unified GUI

**Produktname:** Unified GUI · **Modul:** `ellmos-unified-gui` · **Stand:** 2026-09-09 · **Status:** weitgehend umgesetzt (v0.9.0 plus unveröffentlichte Panels)

---

## 1. Problem

Im Ökosystem existieren heute **fünf getrennte Bedienoberflächen** und mehrere GUI-lose
Steuersysteme, aber keine gemeinsame Steuerzentrale:

| Oberfläche | Kann | Kann NICHT |
|---|---|---|
| BACH-GUI (:8000) | Scheduler/Chains (einziger echter Cron!), Tasks, Prompt-Bibliothek | Agenten starten/steuern, Rechte schalten |
| lock-master-Watcher (:8095) | Locks, Räume, Bulk-Lockdown | Prompts, Modelle, Cron |
| controlcenter-mcp-Dashboard (:3737) | MCP-Profile/Server/Bundles | alles andere |
| ellmos-core (Suite-Web-UI) | Chat, Prompts, Spaces, Personas | Cron, Agent-Dispatch, Rechte-Editor |
| PromptBoard/ProfiPrompt (Desktop) | Prompt-Pflege lokal | Web, Multi-Backend |

Dazu **GUI-lose Steuerlogik**: `bach agent --json` (Dispatch inkl. Rechten/Modell),
ticket-master (Score-Router, Provider-Zuordnung), `LOCK.permissions.json` (Rechte-Engine),
clutch (Modell-Routing), homebase-mcp (Swarm-Pläne, Task-Store).

**Kernfehler, der sich wiederholt hat:** Zwei Produkte in einem Modul.
BACHs GUI ist untrennbar mit BACH verwachsen; ellmos-core bündelt Suite-Kern UND Web-UI.
Beide GUIs sind dadurch nicht eigenständig nutzbar oder importierbar.

## 2. Ziel

**Ein eigenständiges, importierbares GUI-Modul** — die Operator-Steuerzentrale über alle
Backends hinweg. Nicht die fünfte Parallel-GUI, sondern die Kapselung, die die anderen
GUIs schrittweise beerben kann.

**Produktabgrenzung (wichtig):**
- **ellmos-core** = *Endnutzer*-Oberfläche der Sovereign-Suite (Chat, Spaces, Artefakte).
- **Unified GUI** = *Operator*-Konsole (Modelle, Agenten, Prompts, Rechte, Routinen, Tasks, Tickets).
- Beziehung: Unified GUI **importiert** Bausteine (u. a. das Auth/Shell-Gerüst-Muster von
  ellmos-core), Hosts wie BACH **importieren** die Unified GUI. Kein Umbau von ellmos-core.

## 3. Architekturprinzipien

1. **Importierbar statt eingebaut.** Das Modul liefert `create_app()` (Standalone-Server)
   UND `mount(app, prefix)` (Einbettung als Sub-App in einen bestehenden FastAPI-Host,
   z. B. BACHs `gui/server.py` oder ellmos-core). Eine Codebasis, zwei Betriebsarten.
2. **Capability-driven: Nur was das Backend anbietet, wird sichtbar.** Beim Start proben
   Adapter ihre Backends (BACH erreichbar? Ollama läuft? `LOCK.permissions.json` vorhanden?
   ticket-master-Verzeichnis existiert?). Jedes Panel deklariert, welche Capabilities es
   braucht; fehlt das Backend, erscheint das Panel nicht (oder read-only-degradiert).
   Discovery-Quelle für MCP-Fähigkeiten: **controlcenter-mcp** (`controlcenter_list_tools`,
   `controlcenter_list_skills`, `controlcenter_suggest_bundles`,
   `controlcenter_list_governance`).
3. **Adapter statt Direktzugriff.** Panels sprechen nie ein Backend direkt an, sondern den
   Adapter-Vertrag (`docs/ADAPTER-CONTRACT.md`). Neue Backends (eigenes System, weitere
   Stacks) = neuer Adapter, null Panel-Änderung.
4. **Bestehende Wahrheiten bleiben autoritativ.** Die GUI erfindet keine eigenen Stores:
   Prompts leben im profiprompt-v1-Schema/BACH-DB, Rechte in `LOCK.permissions.json`,
   Locks in `LOCK*.txt`, Routinen in BACHs `scheduler_jobs`, Tickets als `T-*.txt`-Dateien.
   Die GUI ist View + Editor, nie zweite Quelle der Wahrheit.
5. **Kein Build-Schritt.** FastAPI + Jinja2/HTMX + Vanilla-JS — das dreifach bewährte
   Muster (lock-master-Watcher, ProfiPrompt web_companion, ellmos-core). Zero-Node-Toolchain.

## 4. Panel-Katalog (Zielbild)

Jedes Panel: eigenes Python-Modul unter `src/unified_gui/panels/`, deklariert
`required_capabilities`, liefert Routen + Template-Fragment.

| # | Panel | Backend/Adapter | Kernfunktionen | Quelle der Bausteine |
|---|---|---|---|---|
| P1 | **Prompts** | BACH prompt-library-API · PromptBoard `library.json` · ProfiPrompt `profiprompt-library-v1.json` | Bibliothek mit Versionierung, 5 Objekttypen (PROMPT/SKILL/WORKFLOW/ROLLE/AGENT), `{{var}}`, Import/Export | ProfiPrompt-Schema (kanonisch), BACH `/api/prompt-library` (seit v3.13.0) |
| P2 | **Agenten** | `bach agent --json` · ellmos-agent-bridge | Start/Stop/Steer/Checkpoint, `permission_mode`/`allowed_tools`, Live-Status, Verlauf | BACH AgentLauncher (fertige JSON-API) |
| P3 | **Modelle** | Ollama `/api/tags` · clutch · proprietäre APIs (Key/Abo) | Modelle listen/hinzufügen, lokale vs. API-Modelle, Verfügbarkeits-Check, Default je Rolle | clutch (Routing/BYOM), Ollama-API |
| P4 | **Routing** | ticket-master-Config · clutch · homebase `hb_route_*` | Score-Formel/Tier→Provider einsehen+ändern, `router_command`, Advisor-Modell, Routing-Statistik | ticket-master `config/*.json`, hb_route_stats |
| P5 | **Berechtigungen** | lock-master `permissions.py` + Watcher-API | `LOCK.permissions.json`-Editor (allow/deny/ask, Pattern, `applies_to_agents`), Locks, Bulk-Lockdown | lock-master (Engine fertig, Editor fehlt) |
| P6 | **Routinen/Cron** | BACH `scheduler_jobs` + Chains (`/api/daemon/*`) | Jobs/Chains CRUD, Intervalle, Run-Historie; **Routine → Modell + Rolle + Skills knüpfen** | BACH-Scheduler (einziger echter), Rolle=Prompt-Objekt (P1), Skills via controlcenter-mcp |
| P7 | **Tasks** | BACH `tasks` · rinnsal `scanner_tasks.db` · homebase `hb_state_task_*` | Aufgaben aus allen Quellen aggregiert anzeigen, Status, **Zuordnung an Agent/Modell** (assign), Provenienz | BACH task-Handler, `_control-center/_tasks`-Scanner, homebase State |
| P8 | **Tickets** | ticket-master (Dateisystem `tickets/`) | Intake-Formular (LLM-Aufgaben-Erfassung), Score-/Routing-Vorschau, Queues (PENDING/QUEUED/SOLVED), Claim-Status je Host | ticket-master v1.9 (Logik fertig, GUI fehlt) |
| P9 | **Skills** | controlcenter-mcp (`list_skills`/`find_skill`) | Skill-Inventar, Intent→Skill-Matching, Bundle-Zuordnung | controlcenter-mcp (fertig) |
| P10 | **Decisions** | TO-DECIDE-Kette über `decision-clicker` · Rückfall: `decisions.index.json` | Übersicht (offen zuerst, Scope-/Status-Filter, Kollisions-Warnung) **plus** Durchklicken, Einstellen, Register und Desktop-Postfach-Übernahme — sobald die Kernlogik da ist; sonst unverändert read-only | decision-clicker (Lib + CLI) über `DECISIONS_RW`; Index-Generator bleibt der eine Parser [D11] |
| P11 | **Skill-Wizard** | `catalog.py` (skills-Repo, Subprozess) | Gerüst anlegen, Pflichtfeld `description:` ausfüllen (Wizard-Fragen "was tut er"/"wann triggert er", gemined aus `skill-creator`s Capture-Intent), statische S-Tests (`--type static`, kein LLM-Aufruf) — der Skill-Körper/die Eval-Schleife bleibt bewusst `skill-creator`s Aufgabe | catalog.py `create`/`quality` (fertig, Wizard schließt nur die Beschreibungs-Lücke) |
| P12 | **Races** | `compare-race` (read-only) | Vorhandene Race-Berichte, Läufe und vorhandene Judge-Urteile anzeigen; kein kostenpflichtiger Start- oder Judge-Automatismus | kanonischer `compare_race.report`-Import |
| P13 | **Chat** | `ellmos-chat` (chat.runtime, Staging-Modul) | v1-Durchstich: eine Frage, eine Antwort über die konfigurierte Chat-Runtime (Backend/Tools/SafetyPolicy bleiben ellmos-chats eigene Sache); kein Verlaufs-UI, kein Modellwechsel im Panel -- nächste Ausbaustufen bewusst nicht Teil von T-20260825-835413946 | ellmos-chat `ChatRuntime.process()` (sys.path-Konsum aus dem Staging-Modul, analog `compare_race.report`) |
| P14 | **Governance** | controlcenter-mcp (`controlcenter_list_governance`) | Fertigen Markdown-Lesespiegel unverändert und sicher maskiert anzeigen; Quellenstatus, Teilständigkeit, Staleness und valides BYUM-Count 0 bleiben sichtbar; keine lokale Föderation, Adoption oder Ausführung | rein lesender MCP-Vertrag; Decision-/Policy-/BYUM-Fachlogik bleibt ausschließlich im ControlCenter-MCP |
| P15 | **Nachrichten** | BACH-REST `/api/messages*` (seit Welle 1 des Modulschnitts D-20260830-002 über `assistant_core.MessageStore`) | Auftragsnachrichten an Agenten anlegen, Antworten (inbox mit `parent_id`) lesen, gelesen/archivieren/löschen — kein eigener Store, Datenhoheit bei `bach.db` | BACH |

### Wheelhouse-Parität Web (Wheelhouse Flat) / Konsole (Wheelhouse Lower Decks) (Stand 2026-08-25, T-20260825-450296633)

Programm Wheelhouse (T-20260825-922806707, K7): Konsole und Web werden
parallel weiterentwickelt, Ziel "gleich weit" -- gemessen als Status je
Panel, nicht als Gesamtprozent. Startzustand nach dem Architektur-Spike:

| Panel | Web (Wheelhouse Flat) | Konsole (Wheelhouse Lower Decks) |
|---|---|---|
| P1-P12 (alle) | vollständig | fehlt |
| P13 (Chat, neu seit T-20260825-835413946) | vollständig | fehlt |
| P14 (Governance, neu seit T-20260826-726630521) | vollständig | fehlt; Folgeticket wird beim Abschluss erfasst |
| P15 (Nachrichten, neu seit Welle 1 Teil 2b, T-20260903-278159544) | vollständig | fehlt |
| P8 (Tickets) | vollständig | **Skelett** (lesender Durchstich, `console/p8_tickets_console.py`, verifiziert gegen den echten Ticket-Bestand) |
| Rollenstart (E01) | kein Web-Panel | **vollständig** (`python -m unified_gui.console start`, direkte `roles[]`, sichtbarer Prozesshost mit klarer Fallback-Kette) |

"Gleich weit" heißt: die Differenz wird über die Roadmap kleiner, nie
größer -- kein neues Web-Feature ohne mitwachsende Konsole-Ticket-Erfassung.
Architekturentscheidung für die Konsole-Seite (Ergebnis des Spikes): siehe
`T-20260825-450296633` (SOLVED) -- dünne CLI-Fassade, die dieselben Adapter
direkt aufruft (kein HTTP-Hop), nicht Textual/TUI und nicht duplizierte
Backend-Logik.

### Antworten auf offene Konzeptfragen (2026-07-11)

- **Task-System-Anbindung wie BACH? → Ja, P7.** Wenn ein Task-Backend vorhanden ist
  (BACH-DB, Scanner-DB, homebase), wird es angezeigt; Tasks sind Agenten/Modellen
  **zuweisbar** (BACH: `task assign`, Scanner: `scanner_tasks.py assign`, homebase:
  `hb_state_task_update`). Mehrere Quellen werden nebeneinander mit Provenienz-Badge
  dargestellt, nicht zwangsvereinheitlicht (Regel 4).
- **ticket-master braucht GUI? → Ja, P8** ist dessen GUI-Modul: Erfassung, Router-Vorschau
  (Score + Provider-Kandidaten), Queue-Board. Schreibzugriff bleibt dateibasiert
  (T-*.txt) — damit bleibt die Multi-Host-Claim-Konvention intakt.
- **lock-master braucht GUI? → Ja, P5.** lock-master hat bereits den Watcher (:8095) für
  Locks/Räume; was fehlt, ist der **Permissions-Editor**. P5 nutzt die Watcher-REST-API
  wo vorhanden (Locks, Scan, Prune, Bulk) und ergänzt den Regel-Editor auf
  `permissions.py`-Basis. Der Watcher bleibt als Standalone bestehen; P5 ist die
  eingebettete Sicht.

## 5. Adapter (Zielbild)

```
src/unified_gui/adapters/
├── base.py            # Adapter-Vertrag: probe() -> Capabilities, health()
├── bach.py            # BACH: prompt-library, agent --json, daemon/scheduler, tasks
├── lock_master.py     # permissions.py-Einbindung + Watcher-REST (:8095)
├── ticket_master.py   # tickets/-Dateisystem + config/*.json
├── clutch.py          # Modell-Routing, Provider
├── ollama.py          # /api/tags, Modell-Pull-Status
├── homebase.py        # MCP stdio: hb_state_task_*, hb_route_*, hb_swarm_*
├── controlcenter.py   # MCP: Skills, Bundles und fertiger Governance-Lesespiegel
├── api_models.py      # proprietäre Modelle (Anthropic/OpenAI/... via Key, Abo-Meta)
└── ellmos_chat.py      # chat.runtime (ellmos-chat, Staging-Modul, sys.path-Konsum) -- REALISIERT (T-20260825-835413946)
```

Vertrag im Detail: `docs/ADAPTER-CONTRACT.md`.

## 6. Datenschemata (kanonisch, nicht neu erfunden)

| Domäne | Kanonisches Schema | Herkunft |
|---|---|---|
| Prompts (Austausch) | `profiprompt-library-v1.json` (Prompts→Versionen→Boards, additiv-stabil) | ProfiPrompt |
| Prompts (leicht) | `library.json` (`items[]`, 5 Typen) — Import-Pfad | PromptBoard |
| Rechte | `LOCK.permissions.json` (deny>ask>allow, agent-neutral) | lock-master |
| Locks | `LOCK*.txt` (exclusive/team/user) | lock-master/Spec |
| Routinen | `scheduler_jobs` + `toolchains` (Intervall, next_run) | BACH |
| Tickets | `T-YYYYMMDD-NN[.HOST].txt` + STATUS/VERLAUF/LOESUNG | ticket-master |
| Agent-Steuerung | `bach agent --json`-Payloads (`available_actions`, `permission_mode`) | BACH |

## 7. Übergangspfad

1. **Phase 0 (erledigt, BACH v3.13.0-bluesky):** BACH-GUI an BACHs eigenes Prompt-System
   angeschlossen (`/prompt-library` + PromptBoard-Import) — Referenz-Implementierung für P1.
2. **Phase 1:** Shell + Adapter-Vertrag + Capability-Discovery; P5 (Berechtigungen) und
   P8 (Tickets) zuerst — größte Lücken, Logik jeweils fertig.
3. **Phase 2:** P7 (Tasks) + P2 (Agenten) über BACH-JSON-API; P6 (Routinen) gegen BACHs
   Daemon-API; Routine→Rolle/Skill-Verknüpfung.
4. **Phase 3:** P3/P4 (Modelle/Routing über clutch, Ollama, API-Keys), P9 (Skills).
5. **Phase 4:** Rückbau-Angebote: BACH mountet Unified GUI (`mount(app, "/control")`),
   ellmos-core bindet sie als Operator-Bereich ein; Alt-Panels werden deprecated.

Details: `TODO.md` (Phasenplan), `DECISIONS.md` (Begründungen), `ARCHITECTURE.md` (Technik).
