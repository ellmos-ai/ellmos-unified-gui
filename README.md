<img src="assets/banner.png" width="100%" alt="Ellmos Unified Gui banner">

[🇩🇪 Deutsch](README_de.md) | 🇬🇧 English

# ellmos Unified GUI

**Importable operator console** for the ellmos/BACH ecosystem: models, agents, prompts,
routing, permissions, routines/cron, tasks, tickets and skills — one surface, fed by
the existing backends. MIT licensed.

> **Status: Phase 1–3 implemented (v0.4.0, 2026-07-11; panel additions through 2026-08-07)**
> — 10 panels run standalone (`python -m unified_gui`, port 8990) and embedded
> (`unified_gui.mount(app)`): P1 prompts, P2 agents, P3 models, P4 routing, P5
> permissions, P6 routines, P7 tasks, P8 tickets, P9 skills, P10 decisions.
> 85/85 tests passing (measured 2026-08-17; some skip locally when a backend like
> Ollama is unreachable). Phase 4 (BACH mount, homebase
> adapter, audit log — see TODO.md) is still open.
>
> **V4-Einordnung:** `ellmos-unified-gui` ist ein `.RUNTIME`-Modul und wird über
> `../../.BUNDLES/` in Stacks komponiert. Es konsumiert `.CONTROL` (Locks, Tickets,
> Tasks) und `.ORCHESTRATION` (Routing) über Adapter, besitzt aber keine eigene
> Fachlogik-Wahrheit.

## Core ideas

- One control center on top of five separate GUIs and several headless control systems —
  not a sixth parallel GUI.
- **Importable by design:** `create_app()` (standalone) and `mount(app, prefix)`
  (embedded into BACH or ellmos-core) — the deliberate antidote to the
  "two products in one module" mistake.
- **Capability-driven panels:** adapters probe their backends; only what a backend
  actually offers becomes visible (discovery via controlcenter-mcp).

## Documents

[KONZEPT.md](KONZEPT.md) (German, canonical) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[docs/ADAPTER-CONTRACT.md](docs/ADAPTER-CONTRACT.md) · [DECISIONS.md](DECISIONS.md) ·
[TODO.md](TODO.md)

**Author:** Lukas Geiger · **License:** MIT
