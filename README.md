<img src="assets/banner.png" width="100%" alt="Ellmos Unified Gui banner">

[🇩🇪 Deutsch](README_de.md) | 🇬🇧 English

[![CI](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/ellmos-ai/unified-gui/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# ellmos Unified GUI

**Importable operator console** for the ellmos/BACH ecosystem: models, agents, prompts,
routing, permissions, routines/cron, tasks, tickets, skills and governance — one surface, fed by
the existing backends. MIT licensed.

> **Status: Phase 1–4 mostly implemented (v0.8.0, verified 2026-08-29; unreleased panel additions through
> 2026-08-29)** — 14 panels run standalone (`python -m unified_gui`, port 8990) and
> embedded (`unified_gui.mount(app)`): P1 prompts, P2 agents, P3 models, P4 routing, P5
> permissions, P6 routines, P7 tasks, P8 tickets, P9 skills, P10 decisions, P11 skill
> wizard, P12 races, P13 chat and P14 governance. The suite collects 204 tests;
> environment-gated integration tests skip when their optional sibling backend is absent.
> Visible German adapter status messages use native umlauts and are regression-tested.
> GitHub-hosted CI is currently blocked before step 1 by the organization's external
> Billing & plans payment/spending-limit gate; the local and projected suites are green.
> Real-mounted into `ellmos-core`
> as of 2026-08-18 (`console_enabled` there, see
> `ellmos-core/src/ellmos_core/console.py`) — the earlier "mount() exists but
> nobody calls it" gap is closed; proven by a cross-repo integration test with
> a genuine ellmos-core login (no fake adapter), see TODO.md. **P11 Skill
> Wizard (2026-08-18):** structured scaffold + description + static
> S-Tests via `catalog.py` (skills repo), never the skill body/eval loop —
> that stays `skill-creator`'s job, see TODO.md. **Audit log for write actions
> (2026-08-18):** every state-changing request
> (POST/PUT/PATCH/DELETE) across every panel is appended to
> `~/.ellmos/unified-gui/audit.jsonl` — who/role, panel+action, outcome,
> duration, argument names only (never values), modeled on
> `ellmos-controlcenter-mcp`'s `gateway-audit.jsonl`, see TODO.md. **P12 Races
> (2026-08-19):** read-only browser over already-run
> `compare-race` races (`PROMPT.md`/`RACE.md`/`RUN-*.md`, judge verdict included
> where filled in) — deliberately no race-trigger/judge automation, see TODO.md.
> **P13 Chat (2026-08-25):** minimal one-question/one-answer pass-through to
> `ellmos-chat`; its backend, tools, safety policy and history remain authoritative there.
> **P14 Governance (2026-08-26):** safely escaped, read-only presentation of the
> exact `controlcenter_list_governance` Markdown contract. Source states, partiality,
> decision staleness and a valid BYUM count of zero remain visible; this UI neither
> parses source files nor adopts advisory pointers.
> Phase 4 remainder (BACH mounting this GUI, homebase adapter) is still open —
> see TODO.md for the concrete, measured reasons (BACH write-lock; homebase's
> `hb_route_*`/`hb_state_task_*` tools not canonical yet).
>
> **V4 classification:** `ellmos-unified-gui` is a `.RUNTIME` module composed into
> stacks through `../../.BUNDLES/`. It consumes `.CONTROL` (locks, tickets, tasks)
> and `.ORCHESTRATION` (routing) through adapters and owns no domain source of truth.

## Wheelhouse

This module is an access point into **ControlRoom** — the decided product name (decision
D-20260817-002: a unified surface over the existing `_control-center` governance/data layer, not
a replacement of it). Reaching ControlRoom has three access layers, one nautical image, three
names:

| Layer | Name | What it is |
|---|---|---|
| Desktop app | **Wheelhouse** | the helm itself — hands on the wheel |
| Web | **Wheelhouse Flat** | the same control room, flat in the browser |
| Console | **Wheelhouse Lower Decks** | the same control room, below deck at the machines |

This module builds the two layers that exist today — Web (**Wheelhouse Flat**, this FastAPI/HTMX
app) and Console (**Wheelhouse Lower Decks**, the `console/` scripts, see *Core ideas* below).
The Desktop app (bare **Wheelhouse**) is not part of this module and does not exist yet; the name
above is reserved for it. Both existing layers are kept developed side by side on purpose
(decision K7, no head start for either) and are steered from the same wheelhouse; a lighthouse
stands for the overview a pilot needs across the whole ecosystem's waters, and the individual
backends this module surfaces — without becoming a sixth parallel GUI itself — are the swimmers
and divers below deck. The technical module name (`ellmos-unified-gui`, import name
`unified_gui`, manifest id unchanged) stays exactly as it is — none of the names above are a
rename. Programme ticket: `_control-center/_TICKETS/.../T-20260825-922806707`.

**Not the same ocean as `open-ocean`.** `ellmos-ai/open-ocean` is a separate, private repository
with its own water image — its README opens with *"it opens when the water reaches the
ocean"*, describing the ecosystem's release-readiness and community-opening roadmap (a maturity
gate: component green -> bundle green -> everything green -> open-ocean). Wheelhouse (in all
three layers) describes *how you steer and reach the existing modules today*; open-ocean
describes *when and how the wider system becomes releasable*. The two images share water, not a
subject, and neither one is a synonym for the other.

*A note on "Lighthouse":* a "Lighthouse" phase name is also used elsewhere in this ecosystem's
release process (part of the component/bundle/system-wide readiness gates above), and that usage
predates this section. Until its exact origin is confirmed, this doc treats the lighthouse above
only as one image inside the Wheelhouse metaphor, not as a claimed product name.

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
Races (read-only `compare-race` race/report browser) · Chat (minimal `ellmos-chat`
pass-through) · Governance (read-only `controlcenter_list_governance` report; no local
federation or adoption).

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
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | Dependency and asset provenance inventory |
| [docs/ai-act-note.md](docs/ai-act-note.md) | Component boundary for AI-related deployments |

## License and provenance

Unless a file says otherwise, the repository-authored code, documentation, prompts and
assets are offered under the [MIT License](LICENSE). Third-party packages are not
relicensed; their own terms are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
The repository includes AI-assisted contributions that were reviewed and edited by a
human maintainer. Before public or commercial use, the owner must still confirm the
source rights for `assets/banner.png`; this preparation does not treat that asset as
cleared merely because it is currently tracked.

## Related modules

`ellmos-core` (suite core/end-user UI, imported as the scaffold precedent) ·
`lock-master` · `ticket-master` · `clutch` · `ellmos-homebase-mcp` ·
`ellmos-controlcenter-mcp` · `compare-race` · BACH (`.AI/.OS/BACH`).

**Author:** Lukas Geiger · **License:** MIT
