---
name: "ellmos-unified-gui"
type: project-docs
profile: "STANDARD"
version: 0.9.0
created: "2026-07-11"
updated: "2026-08-21"
reason_last_change: "Private Public-Readiness und Vertragsabgleich"
last_verified: "2026-08-21"
author: "Lukas Geiger"
anthropic_compatible: true
description: |
  Project-specific instructions for AI coding agents in ellmos-unified-gui.
  Provider-neutral project contract under a compatibility filename. Other
  agents enter through AGENTS.md.
---

# CLAUDE.md — Instructions für AI Coding Agents

> **Selbstkorrektur:** Veraltete Passagen/Verweise autonom korrigieren; Neues so
> dokumentieren, dass der nächste Agent es durch Lesen dieser Dateien findet.

## Projekt

**ellmos Unified GUI** — importierbare Operator-Konsole (Modelle, Agenten, Prompts,
Routing, Berechtigungen, Routinen, Tasks, Tickets, Skills) über Adapter auf die
vorhandenen Backends des Ökosystems.

**Kanonischer Klon (entwickeln/committen/pushen):** `C:\_Local_DEV\repos\unified-gui`
**OneDrive-Arbeits-/Deploykopie (ohne `.git`, Plan D):** `~/OneDrive/.TOPICS/.AI/.MODULES/.RUNTIME/ellmos-unified-gui` — nach jedem Push per robocopy nachziehen (siehe `unified-gui.repo.md` dort)
**Repository:** privat, `https://github.com/ellmos-ai/ellmos-unified-gui` (kanonischer GitHub-Name; lokaler Klonname bleibt `unified-gui`)
**Sprache/Stack:** Python 3.10+, FastAPI + Jinja2/HTMX + Vanilla-JS (KEIN Build-Schritt)

## Rolle & Stil

Arbeite als Senior Dev mit Fokus auf saubere Modul-Grenzen (Adapter-Vertrag!) und
Import-Fähigkeit. Sprache: Deutsch (Code/Identifier englisch), knapp, direkt.

## Einstieg

1. `KONZEPT.md` lesen (Pflicht — Panel-Katalog + Prinzipien)
2. `docs/ADAPTER-CONTRACT.md` vor JEDER Adapter-/Panel-Arbeit
3. `TODO.md` für die aktuelle Phase; `DECISIONS.md` vor Architektur-Abweichungen

## Harte Regeln (aus DECISIONS.md)

- **Kein eigener Fach-Datenstore.** Wahrheit bleibt bei den Backends
  (BACH-DB, `LOCK.permissions.json`, `T-*.txt`, `scheduler_jobs`, profiprompt-v1). [D04]
- **Kein globaler Modul-Zustand** — alles an der App-Instanz (Doppel-Mount!). [D02]
- **Panels nur über Adapter** — nie Backend-Direktzugriff aus einem Panel. [D03]
- **`probe()` wirft nie und antwortet < 2 s.** Fehler = Capability fehlt. [D03]
- **Keine Klartext-API-Keys** in Config/Repo — nur Credential-Referenzen. (ARCHITECTURE §Sicherheit)
- **Kein Framework-Frontend / kein Build-Schritt.** HTMX + Vanilla-JS. [D02]
- Schreibende Aktionen prüfen vorab `LOCK.permissions.json` (lock-master-Adapter).
- **P10 schreibt seit [D11]** — aber nur über die `decision-clicker`-Kernlogik, nie mit
  eigenem Parser. Fehlt das Modul, degradiert P10 auf die read-only-Sicht von [D10].

## Verwandte Systeme (Anbindungsziele)

| Backend | Zugang | Panel |
|---|---|---|
| BACH | `bach agent/task --json`, REST `/api/daemon/*`, `/api/prompt-library` | P1/P2/P6/P7 |
| lock-master | `permissions.py` (Import) + Watcher-REST :8095 | P5 |
| ticket-master | Dateisystem `tickets/`, `config/*.json` | P4/P8 |
| clutch / Ollama | Routing-API / `:11434/api/tags` | P3/P4 |
| homebase-mcp | stdio-MCP (`hb_state_task_*`, `hb_route_*`) | P4/P7 |
| controlcenter-mcp | stdio-MCP (`controlcenter_list_skills`, …) | P9 + Discovery |
| decision-clicker | Lib-Import (`src/decision_clicker/api.py`) + `decisions.index.json` als Rückfall | P10 |

## Tests

`PYTHONIOENCODING=utf-8 python -m pytest tests/` — Pflicht-Testklasse ab Phase 1:
Degradierung (Backend fehlt ⇒ Panel unsichtbar, kein Crash).
