🇩🇪 Deutsch | [🇬🇧 English](README.md)

[![CI](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](LICENSE)

# ellmos Unified GUI

**Importierbare Operator-Konsole** für das ellmos-/BACH-Ökosystem: Modelle, Agenten,
Prompts, Routing, Berechtigungen, Routinen/Cron, Tasks, Tickets und Skills — in einer
Oberfläche, gespeist aus den vorhandenen Backends. MIT-lizenziert.

> **Status: Phase 1–4 größtenteils umgesetzt (v0.8.0, verifiziert 2026-08-21; Panel-Ergänzungen bis
> 2026-08-19)** — 12 Panels laufen standalone (`python -m unified_gui`, Port 8990) und
> eingebettet (`unified_gui.mount(app)`): P1 Prompts, P2 Agenten, P3 Modelle, P4 Routing,
> P5 Berechtigungen, P6 Routinen, P7 Tasks, P8 Tickets, P9 Skills, P10 Entscheidungen,
> P11 Skill-Wizard, P12 Races. 176/176 Tests grün (gemessen 2026-08-21; einzelne werden
> übersprungen, wenn ein Backend wie Ollama lokal nicht erreichbar ist). Seit
> 2026-08-18 real in `ellmos-core` eingehängt (`console_enabled` dort, siehe
> `ellmos-core/src/ellmos_core/console.py`) — die frühere Lücke "mount()
> existiert, aber niemand ruft es auf" ist geschlossen; belegt durch einen
> Cross-Repo-Integrationstest mit echtem ellmos-core-Login (kein Fake-Adapter),
> siehe TODO.md. **P11 Skill-Wizard (2026-08-18):** strukturiertes
> Gerüst + Beschreibung + statische S-Tests über `catalog.py` (skills-Repo) —
> NICHT der Skill-Körper/die Eval-Schleife, das bleibt Aufgabe von
> `skill-creator`, siehe TODO.md. **Audit-Log für Schreibaktionen (2026-08-18):**
> jede zustandsändernde Anfrage
> (POST/PUT/PATCH/DELETE) über alle Panels hinweg landet in
> `~/.ellmos/unified-gui/audit.jsonl` — wer/Rolle, Panel+Aktion, Ergebnis,
> Dauer, nur Argumentnamen (nie -werte), nach dem Vorbild von
> `ellmos-controlcenter-mcp`s `gateway-audit.jsonl`, siehe TODO.md. **P12 Races
> (2026-08-19):** read-only Browser über bereits
> gelaufene `compare-race`-Races (`PROMPT.md`/`RACE.md`/`RUN-*.md`, inkl.
> Judge-Urteil wo ausgefüllt) — bewusst kein Race-Trigger/Judge-Automatismus,
> siehe TODO.md. Restlicher Phase-4-Umfang (BACH mountet diese GUI,
> Homebase-Adapter) ist weiter offen — siehe TODO.md für die konkreten,
> gemessenen Gründe (BACH-Schreibsperre; homebase' `hb_route_*`/
> `hb_state_task_*`-Werkzeuge noch nicht kanonisch).
>
> **V4-Einordnung:** `ellmos-unified-gui` ist ein `.RUNTIME`-Modul und wird über
> `../../.BUNDLES/` in Stacks komponiert. Es konsumiert `.CONTROL` (Locks, Tickets,
> Tasks) und `.ORCHESTRATION` (Routing) über Adapter, besitzt aber keine eigene
> Fachlogik-Wahrheit.

## Idee in drei Sätzen

1. Das Ökosystem hat fünf getrennte GUIs und mehrere GUI-lose Steuersysteme —
   die Unified GUI ist die **eine** Steuerzentrale darüber, nicht die sechste Parallel-GUI.
2. Sie ist **importierbar** (`create_app()` standalone, `mount(app, prefix)` eingebettet
   in BACH oder ellmos-core) — der bewusste Gegenentwurf zum „zwei Produkte in einem
   Modul"-Fehler von BACH-GUI und ellmos-core.
3. Panels erscheinen **capability-driven**: Adapter proben ihre Backends, und nur was
   ein Backend wirklich anbietet, wird sichtbar (Discovery via controlcenter-mcp).

## Panels (Zielbild)

Prompts (versioniert, profiprompt-v1) · Agenten (BACH-Dispatch inkl. Rechten/Steering) ·
Modelle (Ollama + proprietäre APIs via clutch) · Routing (ticket-master-Score/Tiers) ·
Berechtigungen (`LOCK.permissions.json`-Editor, lock-master) · Routinen/Cron
(BACH-Scheduler; Routine → Modell + Rolle + Skills) · Tasks (BACH/Scanner/homebase,
zuweisbar) · Tickets (ticket-master-Intake/Router/Queues) · Skills (controlcenter-mcp) ·
Entscheidungen · Skill-Wizard (Gerüst + Beschreibung + S-Tests über `catalog.py`, skills-Repo) ·
Races (read-only `compare-race`-Report-Browser).

## Multi-System / Cloud (OneDrive)

Die Konfiguration ist **host-neutral**: Pfade in `~`-Notation (oder `$VAR`/`%VAR%`),
Basis-Config liegt geteilt in `~/OneDrive/.TOPICS/_control-center/unified-gui.config.json`
und synct auf alle Systeme — unabhängig vom Namen des Benutzerkontos. Abweichungen
pro System: `unified-gui.config.<HOSTNAME>.json` daneben (geteilt) oder unter
`~/.unified_gui/` (lokal). Fehlende Felder ergänzt
eine Auto-Discovery des Standard-Layouts; Backends, die es auf einem System nicht
gibt, verschwinden ohnehin per Capability-Probe. Start überall:
`_control-center/START-UNIFIED-GUI.bat` (Windows) bzw. `python -m unified_gui`.
**Mac-Hinweis:** OneDrive liegt dort meist unter `~/Library/CloudStorage/...` —
einmalig `~/OneDrive`-Symlink setzen oder Host-Override nutzen.

## Dokumente

| Datei | Inhalt |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Problem, Ziel, Prinzipien, Panel-Katalog, Übergangspfad |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schichten, Capability-Registry, Mount vs. Standalone, Nicht-Ziele |
| [docs/ADAPTER-CONTRACT.md](docs/ADAPTER-CONTRACT.md) | Adapter-Vertrag, Capabilities, Domänen-Mixins |
| [DECISIONS.md](DECISIONS.md) | Entscheidungslog (D01–D11) |
| [TODO.md](TODO.md) | Phasenplan 0–4 |
| [SECURITY.md](SECURITY.md) | Vertrauensgrenzen und Meldung von Schwachstellen |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | Inventar der Abhängigkeiten und Asset-Provenienz |
| [docs/ai-act-note.md](docs/ai-act-note.md) | Komponentengrenze für KI-bezogene Einsätze |

## Lizenz und Provenienz

Sofern eine Datei nichts Abweichendes angibt, stehen der im Repository erstellte Code,
die Dokumentation, Prompts und Assets unter der [MIT-Lizenz](LICENSE). Drittanbieterpakete
werden nicht neu lizenziert; ihre eigenen Bedingungen sind in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) aufgeführt. Das Repository enthält
KI-unterstützte Beiträge, die ein menschlicher Maintainer geprüft und bearbeitet hat.
Vor einer öffentlichen oder kommerziellen Nutzung muss der Eigentümer die Herkunftsrechte
von `assets/banner.png` noch bestätigen; die bloße Aufnahme in Git gilt in dieser
Vorbereitung nicht als Freigabe des Assets.

## Verwandte Module

`ellmos-core` (Suite-Kern/Endnutzer-UI, wird als Gerüst-Vorbild importiert) ·
`lock-master` · `ticket-master` · `clutch` · `ellmos-homebase-mcp` ·
`ellmos-controlcenter-mcp` · `compare-race` · BACH (`.AI/.OS/BACH`).

**Autor:** Lukas Geiger · **Lizenz:** MIT
