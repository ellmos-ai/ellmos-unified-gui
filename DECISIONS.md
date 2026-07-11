# DECISIONS — ellmos Unified GUI

Format: `[ID] Datum — Entscheidung` mit Kontext/Begründung. Neueste oben.

---

## [D07] 2026-07-11 — clutch ist die Modell-/Credential-Registry (kein api_models-Store)

Der geplante api_models-Adapter mit eigener models.json entfaellt: clutch bringt
bereits Provider-neutrale Gears (getriebe.json), einen Credential-Store
(~/.clutch/credentials.json via `clutch keys`, env-first) und Model-Discovery
mit. Eigene Modell-Persistenz in der GUI waere eine zweite Wahrheit (verstoesse
gegen D04). P3 zeigt clutch + Ollama nebeneinander; Schluessel erscheinen nie
in der GUI. homebase-Adapter auf Phase 4 verschoben (Routing/Swarm dort Stubs).

## [D06] 2026-07-11 — Tickets & Locks als Panels, nicht als eigene GUIs dupliziert

ticket-master (kein UI) und lock-master (Watcher nur für Locks) bekommen ihre GUI
**innerhalb** der Unified GUI (P8, P5). lock-masters Watcher bleibt als Standalone
bestehen; P5 nutzt dessen REST-API und ergänzt den fehlenden Permissions-Editor.
Ticket-Schreibzugriffe bleiben dateibasiert (`T-*.txt`), damit die Multi-Host-
Claim-Konvention (Dateiname = Claim) unangetastet funktioniert.
**Quelle:** User-Entscheidung 2026-07-11 („Ticket-Master … braucht auch ein gui modul. lock-master auch.")

## [D05] 2026-07-11 — Task-Panel mit Multi-Quellen-Aggregation und Zuweisung

Tasks aus BACH (`tasks`), Task-Scanner (`~/.rinnsal/scanner_tasks.db`) und homebase
(`hb_state_task_*`) werden nebeneinander mit Provenienz-Badge angezeigt und sind
Agenten/Modellen zuweisbar — aber NICHT in einen neuen Einheits-Store migriert
(Wahrheit bleibt beim Backend). **Quelle:** User-Frage/Entscheidung 2026-07-11.

## [D04] 2026-07-11 — Kanonische Schemata statt Neuerfindung

Prompts: `profiprompt-library-v1.json` (Austausch) + PromptBoard `library.json`
(Import). Rechte: `LOCK.permissions.json`. Routinen: BACH `scheduler_jobs`/Chains.
Tickets: `T-*.txt`. Die GUI hält keine eigene Fach-Persistenz (nur UI-Preferences).
**Begründung:** Jede zweite Quelle der Wahrheit erzeugt Sync-Bugs; die Schemata sind
erprobt und teils published (ProfiPrompt MIT, lock-master MIT).

## [D03] 2026-07-11 — Capability-driven Panels („nur was das Backend anbietet")

Panels deklarieren `required_capabilities`; Adapter melden per `probe()`, was ihr
Backend JETZT kann. Fehlende Backends ⇒ Panel unsichtbar oder degradiert (read-only).
Discovery für MCP-Fähigkeiten läuft über controlcenter-mcp.
**Quelle:** User-Vorgabe („Es müssen nicht immer alle Teile der GUI genutzt werden
und nur das was das Backend auch anbietet wird dann sichtbar").

## [D02] 2026-07-11 — Eigenes Modul statt Umbau von ellmos-core oder BACH-GUI

ellmos-core bleibt Suite-Kern (Endnutzer-Produkt); BACHs GUI bleibt BACH-gebunden.
Die Unified GUI ist ein eigenes, importierbares Modul mit `create_app()` (Standalone)
und `mount(app, prefix)` (Einbettung in BACH/ellmos-core). Damit wird der zweimal
begangene Fehler „zwei Produkte in einem Modul" (BACH-GUI untrennbar, core = Kern+UI)
nicht wiederholt. **Quelle:** User-Entscheidung 2026-07-11 („genau das bachproblem,
dass man die gui jetzt nicht getrennt nutzen kann").

## [D01] 2026-07-11 — Name: Modul `ellmos-unified-gui`, Produkt „Unified GUI"

Kein Rename von ellmos-core (Manifest/Installer/GitHub-Referenzen, und „core" ist
für Auth/Shell/Persistenz korrekt). Der Produktname „Unified GUI" gehört der
Operator-Konsole. ellmos-Präfix, weil das Modul zur ellmos-Familie gehört und
ellmos-core-Bausteine importiert. **Quelle:** User-Präferenz „unified gui" 2026-07-11.
