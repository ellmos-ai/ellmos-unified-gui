# SPDX-License-Identifier: MIT
"""BACH-Adapter: Agenten (CLI-JSON), Tasks, Routinen/Scheduler und Prompts (REST).

Zwei Zugangswege, getrennt geprobt:
- REST (BACH-GUI-Server, Standard :8000): Scheduler (/api/daemon/*), Tasks
  (/api/tasks), Prompt-Bibliothek (/api/prompt-library) — schnell, sauberes JSON.
- CLI (python bach.py ... --json, cwd=system/): Agenten-Steuerung (start/stop/
  steer/checkpoint) und Task-Zuweisung — existiert NUR als CLI. Die Ausgabe ist
  mit Hook-Zeilen (ProSync etc.) verrauscht; extract_json() zieht das JSON heraus.

probe() bleibt schnell: REST mit kurzem Timeout, CLI nur per Dateisystem-Check
(bach.py vorhanden?) — ein echter CLI-Aufruf dauert Sekunden (Startup-Hooks).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import BachConfig
from .base import AdapterError, BaseAdapter


def extract_json(text: str):
    """Zieht das aeusserste JSON-Objekt aus verrauschter CLI-Ausgabe.

    BACH-CLI-Ausgaben enthalten Hook-Zeilen vor/nach dem JSON ("[ProSync] ...",
    "[CLOCK] ..."). Strategie: vom ersten '{' bis zum letzten '}' parsen; wenn
    das scheitert, zeilenweise ab jeder '{'-Zeile versuchen.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    for i, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("{"):
            candidate = "\n".join(text.splitlines()[i:])
            end = candidate.rfind("}")
            if end != -1:
                try:
                    return json.loads(candidate[:end + 1])
                except json.JSONDecodeError:
                    continue
    raise AdapterError("no_json_in_output", text.strip()[:300])


class BachAdapter(BaseAdapter):
    name = "bach"
    label = "BACH (Agenten, Tasks, Routinen, Prompts)"

    def __init__(self, config: BachConfig | None = None) -> None:
        self.config = config or BachConfig()
        self._rest_ok = False
        self._rest_latency_ms: int | None = None
        self._control_ok = False
        self._control_latency_ms: int | None = None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _system_dir(self) -> Path | None:
        if not self.config.bach_root:
            return None
        root = Path(self.config.bach_root).expanduser()
        system = root / "system"
        if (system / "bach.py").is_file():
            return system
        if (root / "bach.py").is_file():  # bach_root zeigt direkt auf system/
            return root
        return None

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            self._rest_ok = self._probe_rest()
        except Exception:  # noqa: BLE001 — probe wirft nie
            self._rest_ok = False
        if self._rest_ok:
            caps |= {
                Capability.SCHEDULER_RW,
                Capability.TASKS_RO,
                Capability.PROMPTS_RW,
                Capability.PROMPTS_VERSIONS,
                Capability.PROMPTS_IMPORT,
                Capability.MESSAGES_RW,
            }
        try:
            self._control_ok = self._probe_control()
        except Exception:  # noqa: BLE001 — probe wirft nie
            self._control_ok = False
        if self._control_ok:
            caps |= {
                Capability.CONTROL_API,
                Capability.CONTROL_SLOTS_RO,
                Capability.CONTROL_WORKERS_RW,
                Capability.CONTROL_ACTIVITY_RO,
            }
        try:
            if self._system_dir() is not None:
                caps |= {Capability.AGENT_DISPATCH, Capability.AGENT_STEER,
                         Capability.TASKS_ASSIGN}
        except Exception:  # noqa: BLE001
            pass
        return caps

    def health(self) -> HealthInfo:
        cli = self._system_dir() is not None
        if self._rest_ok and cli:
            detail = "REST + CLI" + (" + Control-API" if self._control_ok else "")
            return HealthInfo("ok", detail, latency_ms=self._rest_latency_ms)
        if self._rest_ok:
            detail = "REST ok, bach.py nicht gefunden (keine Agenten-Steuerung)" + (
                " (Control-API ok)" if self._control_ok else ""
            )
            return HealthInfo("degraded", detail)
        if cli:
            detail = (
                f"BACH-GUI-Server nicht erreichbar ({self.config.rest_url}) — "
                "Scheduler/Tasks/Prompts inaktiv, Agenten via CLI verfuegbar"
            )
            if self._control_ok:
                detail += ", Control-API erreichbar"
            return HealthInfo("degraded", detail)
        if self._control_ok:
            return HealthInfo("degraded", f"Nur Control-API erreichbar ({self.config.control_url})", latency_ms=self._control_latency_ms)
        return HealthInfo("offline", "weder REST noch bach.py gefunden")

    # ------------------------------------------------------------------
    # REST-Transport
    # ------------------------------------------------------------------
    def _probe_rest(self) -> bool:
        started = time.time()
        try:
            self._rest("/api/status")
        except AdapterError:
            return False
        self._rest_latency_ms = int((time.time() - started) * 1000)
        return True

    def _rest(self, path: str, method: str = "GET", payload: dict | None = None):
        url = self.config.rest_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.config.rest_timeout_s) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise AdapterError("bach_rest_error", f"{exc.code} {path}: {detail}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise AdapterError("bach_rest_unreachable", f"{url}: {exc}") from exc
        try:
            return json.loads(body) if body.strip() else {}
        except json.JSONDecodeError as exc:
            raise AdapterError("bach_rest_bad_json", body[:200]) from exc

    # ------------------------------------------------------------------
    # Control-API-Transport (:8081)
    # ------------------------------------------------------------------
    def _resolve_control_token(self) -> str | None:
        if self.config.control_token:
            return self.config.control_token
        if self.config.control_token_file:
            try:
                token = Path(self.config.control_token_file).expanduser().read_text(encoding="utf-8").strip()
                if token:
                    return token
            except (OSError, UnicodeDecodeError):
                pass
        import os
        env_token = os.environ.get("BACH_CONTROL_API_TOKEN") or os.environ.get("UNIFIED_GUI_BACH_CONTROL_TOKEN")
        if env_token:
            return env_token.strip()
        token_file_env = os.environ.get("BACH_CONTROL_API_TOKEN_FILE") or os.environ.get("UNIFIED_GUI_BACH_CONTROL_TOKEN_FILE")
        if token_file_env:
            try:
                token = Path(token_file_env).expanduser().read_text(encoding="utf-8").strip()
                if token:
                    return token
            except (OSError, UnicodeDecodeError):
                pass
        return None

    def _probe_control(self) -> bool:
        started = time.time()
        try:
            self._control("/api/status")
        except AdapterError:
            return False
        self._control_latency_ms = int((time.time() - started) * 1000)
        return True

    def _control(self, path: str, method: str = "GET", payload: dict | None = None):
        url = self.config.control_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        token = self._resolve_control_token()
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=self.config.control_timeout_s) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            if exc.code == 401:
                raise AdapterError("bach_control_unauthorized", detail or "Control-API-Token fehlt oder ungültig") from exc
            if exc.code == 403:
                raise AdapterError("bach_control_forbidden", detail) from exc
            if exc.code == 404:
                raise AdapterError("bach_control_not_found", detail) from exc
            if exc.code == 409:
                raise AdapterError("bach_control_conflict", detail) from exc
            raise AdapterError("bach_control_error", f"{exc.code} {path}: {detail}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise AdapterError("bach_control_unreachable", f"{url}: {exc}") from exc
        try:
            return json.loads(body) if body.strip() else {}
        except json.JSONDecodeError as exc:
            raise AdapterError("bach_control_bad_json", body[:200]) from exc

    # ------------------------------------------------------------------
    # CLI-Transport (Agenten, Zuweisung)
    # ------------------------------------------------------------------
    def _cli(self, args: list[str]) -> dict:
        system = self._system_dir()
        if system is None:
            raise AdapterError("bach_cli_missing", "bach.py nicht gefunden (bach_root pruefen)")
        cmd = [self.config.python_exe or sys.executable, "bach.py", *args]
        try:
            result = subprocess.run(
                cmd, cwd=str(system), capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=self.config.cli_timeout_s,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterError("bach_cli_timeout", " ".join(args)) from exc
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return extract_json(output)

    # ------------------------------------------------------------------
    # AgentControl (CLI --json)
    # ------------------------------------------------------------------
    def agents(self) -> dict:
        return self._cli(["agent", "list", "--json"])

    def agent_start(self, name: str, model: str | None = None, mode: str | None = None) -> dict:
        args = ["agent", "start", name]
        if model:
            args += ["--model", model]
        if mode:
            args += ["--mode", mode]
        return self._cli(args + ["--json"])

    def agent_stop(self, name: str) -> dict:
        return self._cli(["agent", "stop", name, "--json"])

    def agent_steer(self, name: str, note: str) -> dict:
        return self._cli(["agent", "steer", name, note, "--json"])

    def agent_clear_steer(self, name: str) -> dict:
        return self._cli(["agent", "clear-steer", name, "--json"])

    def agent_checkpoint(self, name: str) -> dict:
        return self._cli(["agent", "checkpoint", name, "--json"])

    # ------------------------------------------------------------------
    # TaskSource (REST lesen, CLI zuweisen/erledigen)
    # ------------------------------------------------------------------
    def tasks(self, status: str = "all", limit: int = 200) -> list[dict]:
        data = self._rest(f"/api/tasks?status={status}&limit={limit}")
        rows = data if isinstance(data, list) else data.get("tasks", data.get("rows", []))
        result = []
        for row in rows or []:
            result.append({
                "id": row.get("id"),
                "title": row.get("title") or row.get("name") or "",
                "status": row.get("status", ""),
                "priority": row.get("priority", ""),
                "assigned_to": row.get("assigned_to") or row.get("partner") or "",
                "category": row.get("category") or "",
                "provenance": "bach",
            })
        return result

    def task_assign(self, task_id: int, target: str) -> dict:
        return self._cli(["task", "assign", str(task_id), "--to", target, "--json"])

    def task_done(self, task_id: int) -> dict:
        return self._cli(["task", "done", str(task_id), "--json"])

    # ------------------------------------------------------------------
    # Nachrichten (REST /api/messages*) -- P15; BACH bedient sie seit Welle 1
    # ueber assistant_core.MessageStore, Datenhoheit bleibt bei bach.db (D04).
    # ------------------------------------------------------------------
    def messages(self, direction: str | None = None, status: str | None = None,
                 partner: str | None = None, include_archived: bool = True, limit: int = 50) -> list[dict]:
        query = []
        if direction:
            query.append(f"direction={direction}")
        if status:
            query.append(f"status={status}")
        if partner:
            query.append(f"partner={partner}")
        query.append(f"include_archived={'true' if include_archived else 'false'}")
        query.append(f"limit={limit}")
        data = self._rest("/api/messages?" + "&".join(query))
        rows = data if isinstance(data, list) else data.get("messages", [])
        return list(rows or [])

    def message_create(self, recipient: str, body: str, subject: str | None = None, priority: int = 0) -> dict:
        return self._rest("/api/messages", "POST",
                          {"recipient": recipient, "subject": subject, "body": body, "priority": priority})

    def message_mark_read(self, msg_id: int) -> dict:
        return self._rest(f"/api/messages/{msg_id}/read", "PUT")

    def message_mark_all_read(self) -> dict:
        return self._rest("/api/messages/mark-all-read", "POST")

    def message_archive(self, msg_id: int) -> dict:
        return self._rest(f"/api/messages/{msg_id}/archive", "PUT")

    def message_delete(self, msg_id: int) -> dict:
        return self._rest(f"/api/messages/{msg_id}/delete", "PUT")

    # ------------------------------------------------------------------
    # Scheduler (REST /api/daemon/*)
    # ------------------------------------------------------------------
    def jobs(self) -> dict:
        return self._rest("/api/daemon/jobs")

    def chains(self) -> dict:
        return self._rest("/api/daemon/chains")

    def runs(self, limit: int = 30) -> dict:
        return self._rest(f"/api/daemon/runs?limit={limit}")

    def daemon_status(self) -> dict:
        return self._rest("/api/daemon/status")

    def create_job(self, payload: dict) -> dict:
        return self._rest("/api/daemon/jobs", method="POST", payload=payload)

    def toggle_job(self, job_id: int) -> dict:
        return self._rest(f"/api/daemon/jobs/{job_id}/toggle", method="PUT")

    def run_job(self, job_id: int) -> dict:
        return self._rest(f"/api/daemon/jobs/{job_id}/run", method="POST")

    def toggle_chain(self, chain_id: int) -> dict:
        return self._rest(f"/api/daemon/chains/{chain_id}/toggle", method="PUT")

    def run_chain(self, chain_id: int) -> dict:
        return self._rest(f"/api/daemon/chains/{chain_id}/run", method="POST")

    # ------------------------------------------------------------------
    # PromptStore (REST /api/prompt-library, seit BACH v3.13.0-bluesky)
    # ------------------------------------------------------------------
    def prompts(self, q: str | None = None, category: str | None = None) -> dict:
        params = []
        if q:
            params.append("q=" + urllib.parse.quote(q))
        if category:
            params.append("category=" + urllib.parse.quote(category))
        suffix = ("?" + "&".join(params)) if params else ""
        return self._rest("/api/prompt-library" + suffix)

    def prompt(self, prompt_id: int) -> dict:
        return self._rest(f"/api/prompt-library/{prompt_id}")

    def prompt_create(self, payload: dict) -> dict:
        return self._rest("/api/prompt-library", method="POST", payload=payload)

    def prompt_update(self, prompt_id: int, payload: dict) -> dict:
        return self._rest(f"/api/prompt-library/{prompt_id}", method="PUT", payload=payload)

    def prompt_delete(self, prompt_id: int) -> dict:
        return self._rest(f"/api/prompt-library/{prompt_id}", method="DELETE")

    def prompt_import_promptboard(self) -> dict:
        return self._rest("/api/prompt-library/import-promptboard", method="POST")

    def export_v1(self) -> dict:
        """Best-effort-Export im profiprompt-library-v1-Stil (ohne Boards —
        BACHs GUI-API kennt keine Boards; Spaces/Boards folgen in Phase 4)."""
        listing = self.prompts()
        prompts = []
        for meta in listing.get("prompts", []):
            detail = self.prompt(meta["id"])
            p = detail.get("prompt", {})
            versions = detail.get("versions", [])
            prompts.append({
                "title": p.get("name"),
                "purpose": p.get("purpose"),
                "text": p.get("text"),
                "tags": (p.get("tags") or "").split(",") if p.get("tags") else [],
                "category": p.get("category"),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
                "versions": [
                    {"version_number": v.get("version_number"), "text": v.get("text"),
                     "tags": (v.get("tags") or "").split(",") if v.get("tags") else [],
                     "created_at": v.get("created_at")}
                    for v in versions
                ],
            })
        return {
            "schema_version": "profiprompt-library-v1",
            "source_app": "ellmos-unified-gui/bach-adapter",
            "prompts": prompts,
            "boards": [],
        }

    # ------------------------------------------------------------------
    # Control-API (:8081) — Slots, Workers, Activity (T-20260926-652455601)
    # ------------------------------------------------------------------
    def control_status(self) -> dict:
        """Liest den globalen Status der Control-API (/api/status)."""
        return self._control("/api/status")

    def control_readiness(self, chat_id: str = "api-delegate") -> dict:
        """Prüft Backend-Verfügbarkeit für eine Session/Worker (/api/readiness)."""
        return self._control(f"/api/readiness?chat_id={urllib.parse.quote(chat_id)}")

    def control_slots(self) -> dict:
        """Liest Slots und dynamische Worker (/api/slots)."""
        return self._control("/api/slots")

    def control_workers(self) -> list[dict]:
        """Liest dynamische Worker (/api/workers)."""
        data = self._control("/api/workers")
        if isinstance(data, list):
            return data
        return data.get("workers", [])

    def control_activity(
        self,
        limit: int = 50,
        offset: int = 0,
        source: list[str] | None = None,
        status: list[str] | None = None,
        since: str | None = None,
        until: str | None = None,
        order: str = "desc",
    ) -> list[dict]:
        """Liest Aktivitätshistorie mit Filterung (/api/activity)."""
        params = [f"limit={limit}", f"offset={offset}", f"order={order}"]
        if source:
            params.append("source=" + urllib.parse.quote(",".join(source)))
        if status:
            params.append("status=" + urllib.parse.quote(",".join(status)))
        if since:
            params.append("since=" + urllib.parse.quote(since))
        if until:
            params.append("until=" + urllib.parse.quote(until))
        query = "&".join(params)
        data = self._control(f"/api/activity?{query}")
        if isinstance(data, list):
            return data
        return data.get("history", [])

    def control_create_worker(self, payload: dict) -> dict:
        """Erstellt einen neuen dynamischen Worker (/api/workers POST)."""
        return self._control("/api/workers", method="POST", payload=payload)

    def control_delete_worker(self, worker_id: str) -> dict:
        """Löscht einen dynamischen Worker (/api/workers/delete POST)."""
        return self._control("/api/workers/delete", method="POST", payload={"id": worker_id})

    def control_toggle_worker(self, worker_id: str, status: str | None = None) -> dict:
        """Pausiert/Reaktiviert einen Worker (/api/workers/toggle POST)."""
        payload: dict[str, str] = {"id": worker_id}
        if status:
            payload["status"] = status
        return self._control("/api/workers/toggle", method="POST", payload=payload)

    def control_stop_worker(self, worker_id: str) -> dict:
        """Stoppt einen Worker (/api/workers/stop POST)."""
        return self._control("/api/workers/stop", method="POST", payload={"id": worker_id})

    def control_run_worker(self, worker_id: str, prompt: str | None = None) -> dict:
        """Startet einen Worker-Lauf (/api/workers/run POST)."""
        payload: dict[str, str] = {"id": worker_id}
        if prompt:
            payload["prompt"] = prompt
        return self._control("/api/workers/run", method="POST", payload=payload)
