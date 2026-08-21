<img src="assets/banner.png" width="100%" alt="Ellmos Unified Gui banner">

[🇩🇪 Deutsch](README_de.md) | 🇬🇧 English

[![CI](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# ellmos Unified GUI

**Importable operator console** for the ellmos/BACH ecosystem: models, agents, prompts,
routing, permissions, routines/cron, tasks, tickets and skills — one surface, fed by
the existing backends. MIT licensed.

> **Status: Phase 1–4 mostly implemented (v0.8.0, verified 2026-08-21; panel additions through
> 2026-08-19)** — 12 panels run standalone (`python -m unified_gui`, port 8990) and
> embedded (`unified_gui.mount(app)`): P1 prompts, P2 agents, P3 models, P4 routing, P5
> permissions, P6 routines, P7 tasks, P8 tickets, P9 skills, P10 decisions, P11 skill
> wizard, P12 races. 175/175 tests passing (measured 2026-08-21; some skip locally
> when a backend like Ollama is unreachable). Real-mounted into `ellmos-core`
> as of 2026-08-18 (`console_enabled` there, see
> `ellmos-core/src/ellmos_core/console.py`) — the earlier "mount() exists but
> nobody calls it" gap is closed; proven by a cross-repo integration test with
> a genuine ellmos-core login (no fake adapter), see TODO.md. **P11 Skill
> Wizard (2026-08-18):** structured scaffold + description + static
> S-Tests via `catalog.py` (skills repo), never the skill body/eval loop —
> that stays `skill-creator`'s job, see TODO.md. **Audit log for write actions
> (2026-08-18, same ticket, Restpaket 2c):** every state-changing request
> (POST/PUT/PATCH/DELETE) across every panel is appended to
> `~/.ellmos/unified-gui/audit.jsonl` — who/role, panel+action, outcome,
> duration, argument names only (never values), modeled on
> `ellmos-controlcenter-mcp`'s `gateway-audit.jsonl`, see TODO.md. **P12 Races
> (2026-08-19, same ticket, Restpaket 2a):** read-only browser over already-run
> `compare-race` races (`PROMPT.md`/`RACE.md`/`RUN-*.md`, judge verdict included
> where filled in) — deliberately no race-trigger/judge automation, see TODO.md.
> Phase 4 remainder (BACH mounting this GUI, homebase adapter) is still open —
> see TODO.md for the concrete, measured reasons (BACH write-lock; homebase's
> `hb_route_*`/`hb_state_task_*` tools not canonical yet).
>
> **V4 classification:** `ellmos-unified-gui` is a `.RUNTIME` module composed into
> stacks through `../../.BUNDLES/`. It consumes `.CONTROL` (locks, tickets, tasks)
> and `.ORCHESTRATION` (routing) through adapters and owns no domain source of truth.

## Core ideas

1. One control center on top of five separate GUIs and several headless control systems —
   the **one** control room, not a sixth parallel GUI.
2. **Importable by design:** `create_app()` (standalone) and `mount(app, prefix)`
   (embedded into BACH or ellmos-core) — the deliberate antidote to BACH-GUI's and
   ellmos-core's "two products in one module" mistake.
3. **Capability-driven panels:** adapters probe their backends; only what a backend
   actually offers becomes visible (discovery via controlcenter-mcp).

## Panels (target picture)

Prompts (versioned, profiprompt-v1) · Agents (BACH dispatch incl. permissions/steering) ·
Models (Ollama + proprietary APIs via clutch) · Routing (ticket-master score/tiers) ·
Permissions (`LOCK.permissions.json` editor, lock-master) · Routines/Cron (BACH
scheduler; routine → model + role + skills) · Tasks (BACH/scanner/homebase, assignable) ·
Tickets (ticket-master intake/router/queues) · Skills (controlcenter-mcp) · Decisions ·
Skill Wizard (scaffold + description + static tests via `catalog.py`, skills repo) ·
Races (read-only `compare-race` race/report browser).

## Multi-system / cloud (OneDrive)

Configuration is **host-neutral**: paths in `~` notation (or `$VAR`/`%VAR%`), the base
config lives shared in `~/OneDrive/.TOPICS/_control-center/unified-gui.config.json` and
syncs to every system, independent of its account name. Per-system overrides:
`unified-gui.config.<HOSTNAME>.json` alongside it (shared) or
under `~/.unified_gui/` (local). Missing fields are filled in by auto-discovery of the
standard layout; backends absent on a given system simply disappear via capability probe.
Start anywhere: `_control-center/START-UNIFIED-GUI.bat` (Windows) or `python -m
unified_gui`. **Mac note:** OneDrive usually lives under `~/Library/CloudStorage/...`
there — set a one-time `~/OneDrive` symlink, or use a host override.

## Documents

| File | Content |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Problem, goal, principles, panel catalogue, transition path (German, canonical) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers, capability registry, mount vs. standalone, non-goals |
| [docs/ADAPTER-CONTRACT.md](docs/ADAPTER-CONTRACT.md) | Adapter contract, capabilities, domain mixins |
| [DECISIONS.md](DECISIONS.md) | Decision log (D01–D11) |
| [TODO.md](TODO.md) | Phase plan 0–4 |
| [SECURITY.md](SECURITY.md) | Trust boundaries and vulnerability reporting |

## Related modules

`ellmos-core` (suite core/end-user UI, imported as the scaffold precedent) ·
`lock-master` · `ticket-master` · `clutch` · `ellmos-homebase-mcp` ·
`ellmos-controlcenter-mcp` · `compare-race` · BACH (`.AI/.OS/BACH`).

**Author:** Lukas Geiger · **License:** MIT
