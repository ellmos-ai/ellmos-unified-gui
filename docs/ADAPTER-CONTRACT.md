# ADAPTER-CONTRACT — Unified GUI Backend-Adapter

**Stand:** 2026-07-11 · **Status:** Spezifikation v0.1 (Konzept)

Jedes Backend wird über genau einen Adapter angebunden. Panels kennen nur diesen
Vertrag — nie das Backend selbst.

## 1. Basis-Vertrag

```python
class BaseAdapter(Protocol):
    name: str                # eindeutig, kebab-case: "bach", "lock-master"
    label: str               # Anzeigename fuer die GUI
    def probe(self) -> set[Capability]:
        """Schnelltest, welche Faehigkeiten das Backend JETZT anbietet.
        MUSS < 2s antworten, DARF NIE werfen (Fehler => leere Menge).
        Ergebnis wird gecacht; Re-Probe per UI-Button/Intervall."""
    def health(self) -> HealthInfo:
        """Status fuer die Leiste: ok|degraded|offline, Version, Latenz, Hinweis."""
```

## 2. Capabilities (v0.1)

| Capability | Bedeutung | Beispiel-Backend |
|---|---|---|
| `PROMPTS_RW` | Prompts lesen/schreiben | BACH prompt-library |
| `PROMPTS_VERSIONS` | Versionshistorie vorhanden | BACH, ProfiPrompt-Export |
| `PROMPTS_IMPORT` | Fremdformat importieren | PromptBoard library.json |
| `AGENT_DISPATCH` | Agent starten/stoppen | BACH `agent start/stop` |
| `AGENT_STEER` | Steer/Checkpoint fuer laufende Agenten | BACH `agent steer` |
| `MODELS_LOCAL` | lokale Modelle listen | Ollama `/api/tags` |
| `MODELS_API` | API-Modelle (Key/Abo) verwalten | api_models |
| `ROUTING_CONFIG` | Routing-Regeln lesen/schreiben | ticket-master, clutch |
| `ROUTING_STATS` | Routing-Statistik | homebase `hb_route_stats` |
| `PERMISSIONS_RW` | `LOCK.permissions.json` lesen/schreiben | lock-master |
| `LOCKS_RW` | Locks anlegen/scannen/prunen/bulk | lock-master-Watcher |
| `SCHEDULER_RW` | Routinen/Jobs/Chains CRUD + run | BACH daemon-API |
| `TASKS_RO` | Tasks lesen | BACH, scanner_tasks.db, homebase |
| `TASKS_ASSIGN` | Task einem Agenten/Modell zuweisen | BACH, scanner_tasks.py |
| `TICKETS_RW` | Tickets erfassen/routen/verschieben | ticket-master |
| `SKILLS_DISCOVERY` | Skills inventarisieren/matchen | controlcenter-mcp |
| `DECISIONS_RO` | TO-DECIDE-Index lesen (kein Schreibpfad) | decisions.index.json |

Regeln: Enum ist **additiv** (nie umbenennen/loeschen). Ein Adapter meldet nur, was
er JETZT wirklich bedienen kann (kein "geplant").

## 3. Domänen-Mixins

Ein Adapter implementiert nur die Mixins seiner gemeldeten Capabilities.
Signaturen (v0.1, gekuerzt):

```python
class PromptStore(Protocol):
    def list(self, q=None, category=None) -> list[PromptMeta]
    def get(self, id) -> PromptDetail           # inkl. versions[]
    def create(self, p: PromptCreate) -> PromptMeta
    def update(self, id, text, tags=None) -> int  # neue Versionsnummer
    def delete(self, id) -> None
    def export_v1(self) -> dict                  # profiprompt-library-v1.json
    def import_items(self, payload) -> ImportReport   # idempotent per Name

class AgentControl(Protocol):
    def list(self) -> list[AgentInfo]            # inkl. available_actions
    def start(self, name, model=None, permission_mode=None, task=None) -> AgentInfo
    def stop(self, name) -> AgentInfo
    def steer(self, name, note) -> None
    def checkpoint(self, name) -> None

class TaskSource(Protocol):
    def list(self, status=None) -> list[TaskInfo]    # TaskInfo.provenance = Adaptername!
    def assign(self, task_id, agent_or_model) -> None   # nur bei TASKS_ASSIGN
    def set_status(self, task_id, status) -> None

class TicketStore(Protocol):
    def intake(self, t: TicketDraft) -> TicketInfo   # schreibt T-*.txt
    def score_preview(self, t: TicketDraft) -> RoutingSuggestion  # Score + Kandidaten
    def queues(self) -> dict[str, list[TicketInfo]]  # PENDING/QUEUED/SOLVED/.USER
    def move(self, ticket_id, queue) -> None
    def claim_status(self, ticket_id) -> str | None  # Host aus Dateinamen

class PermissionStore(Protocol):
    def rules(self, root) -> PermissionRules         # allow/deny/ask
    def set_rule(self, root, kind, pattern, agents="*") -> None
    def remove_rule(self, root, kind, pattern) -> None
    def evaluate(self, root, action, agent) -> Verdict   # delegiert an permissions.py

class Scheduler(Protocol):
    def jobs(self) -> list[JobInfo]
    def chains(self) -> list[ChainInfo]
    def create_job(self, j: JobCreate) -> JobInfo    # inkl. bindings (s.u.)
    def toggle(self, job_id) -> JobInfo
    def run_now(self, job_id) -> RunInfo
    def runs(self, job_id=None) -> list[RunInfo]

class ModelProvider(Protocol):
    def models(self) -> list[ModelInfo]              # local|api, verfuegbar?
    def add_api_model(self, provider, model, credential_ref) -> ModelInfo
    def check(self, model_id) -> HealthInfo

class SkillIndex(Protocol):
    def list(self) -> list[SkillInfo]
    def find(self, intent) -> list[SkillMatch]

class DecisionsIndex(Protocol):
    # P10 -- strikt read-only, kein Schreibpfad im Protokoll.
    def summary(self) -> dict                            # counts/collisions/files, ohne entries[]
    def entries(self, scope=None, status_class=None) -> list[dict]  # gefiltert+sortiert
    def collisions(self) -> list[dict]
    def scopes(self) -> list[str]
```

## 4. Routine-Bindings (P6 — Routine an Modell/Rolle/Skills knüpfen)

`JobCreate.bindings` (optional, GUI-seitige Verknüpfung, gespeichert beim Backend
das den Job hält — bei BACH als Job-Argumente/Metadata):

```json
{
  "model": "ollama/qwen3.5:35b-a3b",
  "role_prompt_ref": {"adapter": "bach", "prompt_id": 42},
  "skills": ["deep-research", "encoding-fix"],
  "skills_source": "controlcenter-mcp"
}
```

Auflösung zur Laufzeit: Rolle = Prompt-Objekt (Typ ROLLE/AGENT) → System-Prompt;
Skills werden dem ausführenden Agenten als Anforderung mitgegeben; fehlende Skills
meldet `SkillIndex.find()` VOR dem Speichern (Validierung in der GUI).

## 5. Fehlersemantik

- Adapter werfen `AdapterError(kind, hint)` — Panels rendern das als Inline-Hinweis,
  nie als 500.
- Backend weg zur Laufzeit → Panel degradiert (Banner "Backend offline", read-only
  Cache-Ansicht wenn vorhanden).
- Schreibaktionen sind **nie** fire-and-forget: Ergebnis wird vom Backend zurückgelesen.
