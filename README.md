[🇩🇪 Deutsch](README_de.md) | 🇬🇧 English

# ellmos Unified GUI

**Importable operator console** for the ellmos/BACH ecosystem: models, agents, prompts,
routing, permissions, routines/cron, tasks, tickets and skills — one surface, fed by
the existing backends. MIT licensed.

> **Status: Phase 1 implemented (v0.1.0)** — panels P5 (permissions) and P8 (tickets) run
> standalone (`python -m unified_gui`, port 8990) and embedded (`unified_gui.mount(app)`); 23 tests green.

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
