# DECISIONS — ellmos Unified GUI

Format: `[ID] Datum — Entscheidung` mit Kontext/Begründung. Neueste oben.

---

## [D11] 2026-08-07 — P10 wird interaktiv: Schreibpfad über die decision-clicker-Kernlogik, nicht über einen zweiten Parser

Ergänzt [D10]: P10 kann jetzt entscheiden, einstellen und das Desktop-Postfach
übernehmen. **Quelle:** Nutzer-Weichenstellung 2026-08-07 („GUI für
Entscheidungsfindung" gehört in die Unified GUI, nicht in ein eigenes Werkzeug).

**Der Kern von [D10] bleibt gültig** — und war der Grund für diesen Zuschnitt.
D10 verbot den Schreibpfad, weil „ein zweiter Parser in der GUI eine zweite
Wahrheit mit eigenem Drift-Risiko wäre" [D04]. Genau das passiert hier nicht:
Der Adapter delegiert an das Modul `decision-clicker`, und dieses lädt den
kanonischen Generator `_DECISIONS/_tools/decisions_index.py` als Modul. Es gibt
weiterhin **einen** Parser; die GUI hat keinen eigenen und keinen Datenstore.
Wahrheit bleibt die TO-DECIDE-Kette.

**Degradierung statt Zwang** [D03]: `probe()` meldet `DECISIONS_RW` nur, wenn
die Kernlogik importierbar UND die Kette bedienbar ist. Fehlt das Modul, ist P10
exakt das read-only-Panel vom 01.08. — gleiche Routen, gleiches Verhalten. Das
Panel bleibt deshalb bei `required={DECISIONS_RO}` sichtbar; die Schreibrouten
antworten dann mit `409 decisions.readonly` statt mit einem Serverfehler.

**Im Schreibbetrieb wird frisch aus der Kette gelesen, nicht aus der JSON.**
Ein Klick schreibt an eine Zeilennummer — eine veraltete `decisions.index.json`
zeigte auf die falsche Stelle und die Entscheidung landete im falschen Eintrag.
Zusätzlich prüft der Schreibpfad die erwartete ID an der Zielzeile
(`expected_id`) und bricht bei Abweichung mit „Ansicht ist veraltet" ab. Die
mtime-gecachte JSON-Sicht aus D10 bleibt für den reinen Lesebetrieb bestehen.

**Geschrieben wird konservativ und nachvollziehbar:** nur das Feld
`ENTSCHEIDUNG DES USERS` plus eine Datumszeile, vorher Sicherung nach
`_decision-archive/_bak/`, kein Überschreiben einer bereits getroffenen
Entscheidung, keine Umformatierung. Fremde `LOCK*.txt` im Kettenordner
blockieren jeden Schreibvorgang; zusätzlich läuft vor jeder Aktion die
Rechteprüfung gegen `LOCK.permissions.json` (`deny` blockt, `ask` verlangt
Bestätigung) — die harte Projektregel für schreibende Aktionen.

**Ein Test weniger, zwei Zusagen mehr:** `test_panel_router_is_get_only` ist
entfallen — er schrieb den alten Zustand fest. An seine Stelle treten Tests, die
die Degradierung belegen (ohne Kernlogik kein `DECISIONS_RW`, Schreibrouten
antworten 409) und dass die alten Leserouten GET-only geblieben sind.

## [D10] 2026-08-01 — P10 Decisions: strikt read-only, keine zweite Wahrheit, mtime-Cache statt Live-Parse der Quelldateien

Panel + Adapter lesen ausschließlich die bereits **generierte** `decisions.index.json`
(`_control-center/_DECISIONS/_tools/`) — nicht die TO-DECIDE-*.txt-Quelldateien selbst.
Damit bleibt der Index-Generator die einzige Stelle, die das Chain-/Kollisions-Parsing
beherrscht [D04]; ein zweiter Parser in der GUI wäre eine zweite Wahrheit mit eigenem
Drift-Risiko. Der Adapter cached nur nach `mtime` (kein Reparse derselben unveränderten
Datei), schreibt nie und bietet keinen Schreibpfad — Panel-Router hat ausschließlich
GET-Routen. Fehlt die Index-Datei oder ist sie kaputt (ungültiges JSON, falsches
`schema`-Feld), liefert `probe()` eine leere Menge und `health()` `offline`/`degraded`;
das Panel bleibt dann unsichtbar (Capability-driven, [D03]) statt abzustürzen.
Default-Sicht zeigt `OFFEN` vor `ENTSCHIEDEN_UMSETZUNG_OFFEN`; `DONE`/`ARCHIVIERT`
werden ausgeblendet, außer per explizitem `status_class`-Filter angefordert — sonst
fluten sie die Ansicht (140 von 194 Einträgen im Live-Index waren zum Zeitpunkt der
Entscheidung `DONE`/`ARCHIVIERT`). ID-Kollisionen aus dem Index (`collisions[]`) werden
sichtbar als Warnung ausgewiesen, nicht stillschweigend deduped. **Quelle:** Auftrag
„Read-only-Panel P10 Decisions" 2026-08-01.

## [D09] 2026-07-14 — Scanner-Tasks: Bearbeiter ≠ Anleger, Schema-tolerant lesen, DB-Pfad aus TASKPLAN

Drei Festlegungen aus der Anpassung an TASKPLAN 0.3 (Tasks 40/41/42). Zwei davon
weichen bewusst von der ursprünglichen Vorgabe in TODO.md ab — die Abweichung ist
belegt, nicht Geschmack:

**1. Der Bearbeiter-Fallback prüft den Anleger mit.** `assigned_to` ist die
Wahrheit. TODO.md schlug vor, ersatzweise auf `agent_id` zurückzufallen. Das
reproduziert den Bug in weicher Form: `agent_id` trägt bei nicht zugewiesenen
Tasks den ANLEGER (`scanner`) — im Bestand bei 25 von 44 Tasks, die dann fälschlich
„→ scanner" als Bearbeiter zeigten. Ein Rückfall gilt deshalb nur, wenn `agent_id`
weder ein Anleger-Sentinel (`""`/`default`/`scanner`) noch gleich `created_by` ist.
Erst dann bleibt übrig, was der alte Wrapper dort hinterließ: ein echter
Bearbeiter (`sonnet`, `claude-opus`, …). Der `created_by`-Vergleich allein genügt
NICHT — 22 Alt-Tasks haben `agent_id='scanner'` bei leerem `created_by`.

**2. Spalten werden gesnifft, nicht vorausgesetzt.** Der Adapter öffnet die Queue
strikt read-only (`mode=ro`) und kann eine alte DB daher nie selbst migrieren — er
hängt davon ab, dass ein anderes System das getan hat. Da die GUI ausdrücklich
multi-system läuft [D08], wählt er die Spalten nach `PRAGMA table_info`: eine
nicht migrierte Queue zeigt weniger, statt das Panel mit `no such column`
stillzulegen. Beide Schemata sind getestet.

**3. DB-Pfad: `configured_db_path()`, NICHT `get_default_db_path()`.** TODO.md nannte
Letzteres. Dessen letzter Schritt fällt aber auf `~/.taskplan/taskplan.db` zurück —
im Bestand eine LEERE DB (`taskplan doctor`: 0 Tasks) — und legt das Verzeichnis
dabei auch noch an. Die GUI läse dann ohne Fehler und ohne Warnung eine leere Queue:
dasselbe Drift-Risiko, nur andersherum. Reihenfolge daher `TASKPLAN_DB` >
`[storage] path` > `RINNSAL_DB` > `~/.rinnsal/scanner_tasks.db` (Altpfad statt leerer
Default-DB). Der Aufruf sitzt IN `_apply_discovery`, nicht im Modul-Literal — sonst
fröre er beim Import ein. Ebenso entfernt: der explizite `db_path` in der geteilten
`_control-center/unified-gui.config.json`. Er überstimmte jede Auflösung
(explizite Werte schlagen die Discovery) und hätte den Fix wirkungslos gemacht.

## [D08] 2026-07-11 — Cloud-/Multi-System-Konfiguration: Kaskade + ~-Notation + Discovery

Das Oekosystem synct via OneDrive auf mehrere Systeme mit ABWEICHENDEN
Home-Pfaden (WORKSTATION: `<account-1>`, LAPTOP: `<account-2>`, Mac: `<account-3>`). Deshalb: (1) alle
Pfadfelder expandieren ~/$VAR/%VAR% — Configs werden in ~-Notation
geschrieben und funktionieren unveraendert auf jedem System; (2) Config-
Kaskade Shared(OneDrive, synct) < Shared-Host < User(~/.unified_gui) <
User-Host < cwd < Env < Overrides — Host-Dateien (config.<HOSTNAME>.json)
erlauben Abweichungen pro System ohne die Basis zu forken; (3) Auto-
Discovery ergaenzt fehlende Felder mit dem Standard-Layout (probe()
filtert Nichtexistentes), abschaltbar via discovery=false /
UNIFIED_GUI_DISCOVERY=0; UNIFIED_GUI_CONFIG ersetzt die Kaskade exklusiv
(Test-Hermetik). Mac-Vorbehalt: OneDrive liegt dort meist unter
~/Library/CloudStorage/... — dort Host-/User-Override oder Symlink ~/OneDrive.
**Quelle:** User-Anforderung 2026-07-11 („cloudsensitiv ... configs pro System").

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
