🇩🇪 Deutsch | [🇬🇧 English](README.md)

# ellmos Unified GUI

**Importierbare Operator-Konsole** für das ellmos-/BACH-Ökosystem: Modelle, Agenten,
Prompts, Routing, Berechtigungen, Routinen/Cron, Tasks, Tickets und Skills — in einer
Oberfläche, gespeist aus den vorhandenen Backends. MIT-lizenziert.

> **Status: Phase 1–3 umgesetzt (v0.4.0, 2026-07-11; Panel-Ergänzungen bis 2026-08-07)**
> — 10 Panels laufen standalone (`python -m unified_gui`, Port 8990) und eingebettet
> (`unified_gui.mount(app)`): P1 Prompts, P2 Agenten, P3 Modelle, P4 Routing,
> P5 Berechtigungen, P6 Routinen, P7 Tasks, P8 Tickets, P9 Skills, P10 Entscheidungen.
> 107/107 Tests grün (gemessen 2026-08-18; einzelne werden übersprungen, wenn ein
> Backend wie Ollama lokal nicht erreichbar ist). Seit 2026-08-18 real in
> `ellmos-core` eingehängt (`console_enabled` dort, siehe
> `ellmos-core/src/ellmos_core/console.py`) — die frühere Lücke "mount()
> existiert, aber niemand ruft es auf" ist geschlossen; belegt durch einen
> Cross-Repo-Integrationstest mit echtem ellmos-core-Login (kein Fake-Adapter),
> siehe TODO.md. Restlicher Phase-4-Umfang (BACH-Mount, Homebase-Adapter,
> Audit-Log — siehe TODO.md) ist weiter offen.
> Konfiguration: `unified-gui.config.example.json` kopieren oder `UNIFIED_GUI_*`-Env setzen.

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
zuweisbar) · Tickets (ticket-master-Intake/Router/Queues) · Skills (controlcenter-mcp).

## Multi-System / Cloud (OneDrive)

Die Konfiguration ist **host-neutral**: Pfade in `~`-Notation (oder `$VAR`/`%VAR%`),
Basis-Config liegt geteilt in `~/OneDrive/.TOPICS/_control-center/unified-gui.config.json`
und synct auf alle Systeme — unabhaengig davon, ob das Home `lukas`, `User` oder
etwas anderes ist. Abweichungen pro System: `unified-gui.config.<HOSTNAME>.json`
daneben (shared) oder unter `~/.unified_gui/` (lokal). Fehlende Felder ergaenzt
eine Auto-Discovery des Standard-Layouts; Backends, die es auf einem System nicht
gibt, verschwinden ohnehin per Capability-Probe. Start ueberall:
`_control-center/START-UNIFIED-GUI.bat` (Windows) bzw. `python -m unified_gui`.
**Mac-Hinweis:** OneDrive liegt dort meist unter `~/Library/CloudStorage/...` —
einmalig `~/OneDrive`-Symlink setzen oder Host-Override nutzen.

## Dokumente

| Datei | Inhalt |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Problem, Ziel, Prinzipien, Panel-Katalog, Übergangspfad |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schichten, Capability-Registry, Mount vs. Standalone, Nicht-Ziele |
| [docs/ADAPTER-CONTRACT.md](docs/ADAPTER-CONTRACT.md) | Adapter-Vertrag, Capabilities, Domänen-Mixins |
| [DECISIONS.md](DECISIONS.md) | Entscheidungslog (D01–D06) |
| [TODO.md](TODO.md) | Phasenplan 0–4 |

## Verwandte Module

`ellmos-core` (Suite-Kern/Endnutzer-UI, wird als Gerüst-Vorbild importiert) ·
`lock-master` · `ticket-master` · `clutch` · `ellmos-homebase-mcp` ·
`ellmos-controlcenter-mcp` · BACH (`.AI/.OS/BACH`).

**Autor:** Lukas Geiger · **Lizenz:** MIT
