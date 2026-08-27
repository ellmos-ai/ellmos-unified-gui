# SPDX-License-Identifier: MIT
"""controlcenter-mcp-Adapter: Read-only-Sichten des ControlCenter-MCP.

Spawnt den Node-Server pro Aufruf als stdio-MCP-Session (kurzlebig, kein
Daemon-Management). probe() prueft nur das Dateisystem (Node-Start dauert) —
Fehler zeigen sich als AdapterError im Panel, nicht als Crash.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import ControlCenterConfig
from ..mcp_client import McpError, McpStdioClient
from .base import AdapterError, BaseAdapter


@dataclass(frozen=True)
class GovernanceReport:
    """Fertiger MCP-Bericht ohne lokale Governance-Neubewertung."""

    text: str
    media_type: str = "text/markdown"
    read_only: bool = True


class ControlCenterAdapter(BaseAdapter):
    name = "controlcenter"
    label = "ControlCenter-MCP (Skills & Governance)"

    def __init__(self, config: ControlCenterConfig | None = None) -> None:
        self.config = config or ControlCenterConfig()
        self._ready = False

    def _script(self) -> Path | None:
        if not self.config.repo_path:
            return None
        script = Path(self.config.repo_path).expanduser() / "dist" / "index.js"
        return script if script.is_file() else None

    @staticmethod
    def _built_server_has(script: Path, tool: str) -> bool:
        """Prueft billig, ob das gebaute Bundle den neuen Toolnamen enthaelt."""
        try:
            return tool in script.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            script = self._script()
            self._ready = script is not None and shutil.which(self.config.node_exe) is not None
            if self._ready:
                caps.add(Capability.SKILLS_DISCOVERY)
                if self._built_server_has(script, "controlcenter_list_governance"):
                    caps.add(Capability.GOVERNANCE_RO)
        except Exception:  # noqa: BLE001 — probe wirft nie
            self._ready = False
        return caps

    def health(self) -> HealthInfo:
        if self._ready:
            return HealthInfo("ok", f"{self._script()}")
        if self._script() is None:
            return HealthInfo("offline", "dist/index.js nicht gefunden (repo_path pruefen / npm run build)")
        return HealthInfo("offline", f"node nicht im PATH ({self.config.node_exe})")

    # ------------------------------------------------------------------
    def _call(self, tool: str, arguments: dict | None = None):
        script = self._script()
        if script is None:
            raise AdapterError("controlcenter_missing", str(self.config.repo_path))
        try:
            with McpStdioClient([self.config.node_exe, str(script)],
                                cwd=str(script.parent.parent),
                                timeout_s=self.config.timeout_s) as client:
                result = client.call_tool(tool, arguments or {})
                return result.json() if result.json() is not None else {"text": result.text}
        except McpError as exc:
            raise AdapterError("controlcenter_mcp_error", str(exc)) from exc

    # ------------------------------------------------------------------
    # SkillIndex
    # ------------------------------------------------------------------
    def skills(self):
        return self._call("controlcenter_list_skills")

    def find_skill(self, intent: str):
        return self._call("controlcenter_find_skill", {"intent": intent})

    def bundles(self):
        return self._call("controlcenter_list_bundles")

    # ------------------------------------------------------------------
    # Governance-Lesespiegel
    # ------------------------------------------------------------------
    def governance(self) -> GovernanceReport:
        """Gibt den fertigen MCP-Markdownvertrag unveraendert weiter.

        Quellenstatus, Vollstaendigkeit, Staleness und BYUM-Zaehler werden
        absichtlich nicht lokal geparst oder neu berechnet. Die fachliche
        Autoritaet bleibt damit beim ControlCenter-MCP.
        """
        result = self._call("controlcenter_list_governance")
        text = result.get("text") if isinstance(result, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise AdapterError(
                "controlcenter_contract_error",
                "controlcenter_list_governance lieferte keinen Markdown-Bericht",
            )
        return GovernanceReport(text=text)
