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
            return HealthInfo("ok", "REST + CLI", latency_ms=self._rest_latency_ms)
        if self._rest_ok:
            return HealthInfo("degraded", "REST ok, bach.py nicht gefunden (keine Agenten-Steuerung)")
        if cli:
            return HealthInfo("degraded",
                              f"BACH-GUI-Server nicht erreichbar ({self.config.rest_url}) — "
                              "Scheduler/Tasks/Prompts inaktiv, Agenten via CLI verfügbar")
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
