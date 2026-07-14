# SPDX-License-Identifier: MIT
"""Scanner-Task-Adapter: Hintergrund-Aufgaben-Scanner (_control-center/_tasks).

Backing-Store ist die Rinnsal-SQLite (~/.rinnsal/scanner_tasks.db). Lesen geht
direkt read-only auf die DB (schnell, probe-tauglich); Zuweisen/Erledigen laeuft
ueber das kanonische CLI scanner_tasks.py (Wahrheit + Regeln bleiben dort).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import ScannerTasksConfig
from .base import AdapterError, BaseAdapter

# Spalten des Ur-Schemas (Rinnsal) und die, die TASKPLAN 0.3 ergaenzt hat.
# Der Adapter liest strikt read-only (mode=ro) und kann eine alte DB deshalb
# nie selbst migrieren — er muss mit ihr leben koennen. Ein harter SELECT auf
# die neuen Spalten wuerde das Task-Panel auf einem noch nicht migrierten
# System komplett stilllegen (no such column), statt bloss weniger zu zeigen.
BASE_COLUMNS = ("id", "title", "description", "status", "priority", "agent_id",
                "tags", "created_at", "updated_at")
V03_COLUMNS = ("assigned_to", "created_by", "delegation_status", "effort",
               "scope", "project_path", "root_id")

# Werte, die in agent_id KEINEN Bearbeiter bezeichnen: Vor TASKPLAN 0.3 trug
# agent_id drei Bedeutungen (Anleger, Bearbeiter, Rolle). Bei nicht zugewiesenen
# Tasks steht dort der Anleger ("scanner") oder der Platzhalter ("default") —
# der echte Bearbeiter landete dort nur, weil der alte Wrapper agent_id beim
# Zuweisen ueberschrieb. Ein blosser `assigned_to or agent_id`-Fallback zeigt
# deshalb den Anleger als Bearbeiter: im Bestand 25 von 44 Tasks.
CREATOR_SENTINELS = frozenset({"", "default", "scanner"})


def _assignee(data: dict) -> str:
    """Der Bearbeiter — nie der Anleger.

    `assigned_to` (TASKPLAN 0.3) ist die Wahrheit. Solange es leer ist, gilt
    agent_id nur dann als Bearbeiter, wenn es weder ein Anleger-Sentinel noch
    der Anleger selbst ist (Altbestand: dort ueberschrieb der alte Wrapper
    agent_id beim Zuweisen, ein echter Bearbeiter steht also noch drin).
    """
    assigned = (data.get("assigned_to") or "").strip()
    if assigned:
        return assigned
    legacy = (data.get("agent_id") or "").strip()
    creator = (data.get("created_by") or "").strip()
    if legacy in CREATOR_SENTINELS or legacy == creator:
        return ""
    return legacy


class ScannerTasksAdapter(BaseAdapter):
    name = "scanner-tasks"
    label = "Task-Scanner (Rinnsal-Queue)"

    def __init__(self, config: ScannerTasksConfig | None = None) -> None:
        self.config = config or ScannerTasksConfig()

    def _db(self) -> Path | None:
        if not self.config.db_path:
            return None
        path = Path(self.config.db_path).expanduser()
        return path if path.is_file() else None

    def _tool(self) -> Path | None:
        if not self.config.tool_path:
            return None
        path = Path(self.config.tool_path).expanduser()
        return path if path.is_file() else None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            if self._db() is not None:
                caps.add(Capability.TASKS_RO)
                if self._tool() is not None:
                    caps.add(Capability.TASKS_ASSIGN)
        except Exception:  # noqa: BLE001 — probe wirft nie
            pass
        return caps

    def health(self) -> HealthInfo:
        db = self._db()
        if db is None:
            return HealthInfo("offline", "scanner_tasks.db nicht gefunden")
        if self._tool() is None:
            return HealthInfo("degraded", f"{db} (read-only: scanner_tasks.py fehlt)")
        return HealthInfo("ok", str(db))

    # ------------------------------------------------------------------
    # TaskSource
    # ------------------------------------------------------------------
    def tasks(self, status: str | None = None, limit: int = 200) -> list[dict]:
        db = self._db()
        if db is None:
            raise AdapterError("scanner_db_missing", str(self.config.db_path))
        # read-only oeffnen: niemals schreiben, auch nicht implizit (WAL etc.)
        uri = f"file:{db.as_posix()}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            # Nur Spalten selektieren, die es in DIESER DB gibt: eine noch nicht
            # auf TASKPLAN 0.3 migrierte Queue zeigt dann weniger, statt zu brechen.
            present = {row[1] for row in conn.execute("PRAGMA table_info(rinnsal_tasks)")}
            columns = [c for c in (*BASE_COLUMNS, *V03_COLUMNS) if c in present]
            if not columns:
                raise AdapterError("scanner_db_error", "Tabelle rinnsal_tasks fehlt")
            sql = f"SELECT {', '.join(columns)} FROM rinnsal_tasks"
            params: list = []
            if status:
                sql += " WHERE status = ?"
                params.append(status)
            sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            sql += "WHEN 'medium' THEN 2 ELSE 3 END, id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            conn.close()
        except sqlite3.Error as exc:
            raise AdapterError("scanner_db_error", str(exc)) from exc
        result = []
        for row in rows:
            data = dict(row)
            result.append({
                "id": data["id"],
                "title": data["title"],
                "status": data["status"],
                "priority": data["priority"],
                "assigned_to": _assignee(data),
                "created_by": (data.get("created_by") or "").strip(),
                "delegation_status": (data.get("delegation_status") or "").strip(),
                # effort/scope entscheiden, ob ein Loop die Aufgabe autonom anfasst:
                # leeres effort = uneingestuft = wird nie bearbeitet.
                "effort": (data.get("effort") or "").strip(),
                "scope": (data.get("scope") or "").strip(),
                "project_path": (data.get("project_path") or "").strip(),
                "root_id": (data.get("root_id") or "").strip(),
                "category": data.get("tags") or "",
                "provenance": "scanner",
            })
        return result

    def _cli(self, args: list[str]) -> dict:
        tool = self._tool()
        if tool is None:
            raise AdapterError("scanner_tool_missing", str(self.config.tool_path))
        cmd = [self.config.python_exe or sys.executable, str(tool), *args]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise AdapterError("scanner_cli_timeout", " ".join(args)) from exc
        if result.returncode != 0:
            raise AdapterError("scanner_cli_failed",
                               (result.stderr or result.stdout or "").strip()[:300])
        output = (result.stdout or "").strip()
        try:
            return json.loads(output) if output.startswith("{") or output.startswith("[") else {"output": output}
        except json.JSONDecodeError:
            return {"output": output}

    def task_assign(self, task_id: int, target: str) -> dict:
        return self._cli(["assign", str(task_id), target])

    def task_done(self, task_id: int) -> dict:
        return self._cli(["done", str(task_id)])
