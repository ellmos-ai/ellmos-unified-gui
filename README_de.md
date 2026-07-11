🇩🇪 Deutsch | [🇬🇧 English](README.md)

# ellmos Unified GUI

**Importierbare Operator-Konsole** für das ellmos-/BACH-Ökosystem: Modelle, Agenten,
Prompts, Routing, Berechtigungen, Routinen/Cron, Tasks, Tickets und Skills — in einer
Oberfläche, gespeist aus den vorhandenen Backends. MIT-lizenziert.

> **Status: Phase 1 umgesetzt (v0.1.0)** — Panels P5 (Berechtigungen) und P8 (Tickets) laufen
> standalone (`python -m unified_gui`, Port 8990) und eingebettet (`unified_gui.mount(app)`); 23 Tests grün.
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
