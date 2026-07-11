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
            sql = ("SELECT id, title, description, status, priority, agent_id, tags, "
                   "created_at, updated_at FROM rinnsal_tasks")
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
        return [{
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "priority": row["priority"],
            "assigned_to": row["agent_id"] if row["agent_id"] != "default" else "",
            "category": row["tags"] or "",
            "provenance": "scanner",
        } for row in rows]

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
