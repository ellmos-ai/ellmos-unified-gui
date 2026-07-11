# SPDX-License-Identifier: MIT
"""Minimaler stdio-MCP-Client (JSON-RPC 2.0, newline-delimited).

Genug fuer Adapter-Zwecke: Server spawnen, initialize-Handshake, tools/call,
sauber beenden. Kein Streaming, keine Notifications-Verarbeitung, keine
Resources — bewusst schmal (Panels brauchen nur Tool-Aufrufe).
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import queue
from dataclasses import dataclass

PROTOCOL_VERSION = "2024-11-05"


class McpError(Exception):
    pass


@dataclass
class McpToolResult:
    raw: dict

    @property
    def text(self) -> str:
        """Konkateniert alle text-Contents des Ergebnisses."""
        parts = []
        for item in (self.raw.get("content") or []):
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)

    def json(self):
        """Versucht, den Text-Content als JSON zu parsen."""
        text = self.text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


class McpStdioClient:
    """Ein Client pro Server-Prozess. Nutzung:

        with McpStdioClient(["node", "dist/index.js"], cwd=repo) as client:
            result = client.call_tool("controlcenter_list_skills", {})
    """

    def __init__(self, command: list[str], cwd: str | None = None,
                 env: dict | None = None, timeout_s: float = 20.0) -> None:
        self.command = command
        self.cwd = cwd
        self.env = env
        self.timeout_s = timeout_s
        self._proc: subprocess.Popen | None = None
        self._responses: "queue.Queue[dict]" = queue.Queue()
        self._reader: threading.Thread | None = None
        self._next_id = 0

    # ------------------------------------------------------------------
    def __enter__(self) -> "McpStdioClient":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def start(self) -> None:
        try:
            self._proc = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env={**os.environ, **(self.env or {})},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except (OSError, ValueError) as exc:
            raise McpError(f"Server-Start fehlgeschlagen: {exc}") from exc

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        result = self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "ellmos-unified-gui", "version": "0.3.0"},
        })
        if "error" in result:
            raise McpError(f"initialize fehlgeschlagen: {result['error']}")
        self._notify("notifications/initialized", {})

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    # ------------------------------------------------------------------
    def _read_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # Log-Zeilen des Servers ignorieren
            if isinstance(message, dict) and "id" in message:
                self._responses.put(message)

    def _send(self, payload: dict) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise McpError("Server nicht gestartet")
        try:
            self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        except OSError as exc:
            raise McpError(f"Senden fehlgeschlagen: {exc}") from exc

    def _request(self, method: str, params: dict) -> dict:
        self._next_id += 1
        request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while True:
            try:
                message = self._responses.get(timeout=self.timeout_s)
            except queue.Empty:
                raise McpError(f"Timeout ({self.timeout_s}s) bei {method}")
            if message.get("id") == request_id:
                return message

    def _notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    # ------------------------------------------------------------------
    def call_tool(self, name: str, arguments: dict | None = None) -> McpToolResult:
        response = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in response:
            raise McpError(str(response["error"]))
        return McpToolResult(raw=response.get("result") or {})

    def list_tools(self) -> list[dict]:
        response = self._request("tools/list", {})
        if "error" in response:
            raise McpError(str(response["error"]))
        return (response.get("result") or {}).get("tools", [])
