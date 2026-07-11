---
name: "ellmos-unified-gui"
type: project-docs
profile: "STANDARD"
version: 0.1.0
created: "2026-07-11"
updated: "2026-07-11"
reason_last_change: "Initiale Anlage (Konzept + Ordnerstruktur)"
last_verified: "2026-07-11"
author: "Lukas Geiger"
anthropic_compatible: true
description: |
  Project-specific instructions for AI coding agents in ellmos-unified-gui.
  Primary audience: Claude Code. Other agents redirect here via AGENTS.md.
---

# CLAUDE.md — Instructions für AI Coding Agents

> **Selbstkorrektur:** Veraltete Passagen/Verweise autonom korrigieren; Neues so
> dokumentieren, dass der nächste Agent es durch Lesen dieser Dateien findet.

## Projekt

**ellmos Unified GUI** — importierbare Operator-Konsole (Modelle, Agenten, Prompts,
Routing, Berechtigungen, Routinen, Tasks, Tickets, Skills) über Adapter auf die
vorhandenen Backends des Ökosystems.

**Pfad:** `C:\Users\lukas\OneDrive\.TOPICS\.AI\.MODULES\ellmos-unified-gui`
**Repository:** privat, kein Remote (Release später als `ellmos-ai/unified-gui` geplant)
**Sprache/Stack:** Python 3.11+, FastAPI + Jinja2/HTMX + Vanilla-JS (KEIN Build-Schritt)

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

## Verwandte Systeme (Anbindungsziele)

| Backend | Zugang | Panel |
|---|---|---|
| BACH | `bach agent/task --json`, REST `/api/daemon/*`, `/api/prompt-library` | P1/P2/P6/P7 |
| lock-master | `permissions.py` (Import) + Watcher-REST :8095 | P5 |
| ticket-master | Dateisystem `tickets/`, `config/*.json` | P4/P8 |
| clutch / Ollama | Routing-API / `:11434/api/tags` | P3/P4 |
| homebase-mcp | stdio-MCP (`hb_state_task_*`, `hb_route_*`) | P4/P7 |
| controlcenter-mcp | stdio-MCP (`controlcenter_list_skills`, …) | P9 + Discovery |

## Tests

`PYTHONIOENCODING=utf-8 python -m pytest tests/` — Pflicht-Testklasse ab Phase 1:
Degradierung (Backend fehlt ⇒ Panel unsichtbar, kein Crash).
