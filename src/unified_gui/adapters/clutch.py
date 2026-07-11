# SPDX-License-Identifier: MIT
"""clutch-Adapter: Modell-Registry + Routing (provider-neutral, auto-lernend).

clutch ist die kanonische Modell-Wahrheit (Gears in getriebe.json, Credentials
in ~/.clutch/credentials.json via `clutch keys` — die GUI zeigt NIE Schluessel,
nur Provider-/Referenz-Status). Zugang: CLI `python -m clutch.cli ... --json`
mit cwd=clutch-Repo (kein pip-Paket noetig).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ..capabilities import Capability, HealthInfo
from ..config import ClutchConfig
from .base import AdapterError, BaseAdapter


class ClutchAdapter(BaseAdapter):
    name = "clutch"
    label = "clutch (Modelle & Routing)"

    def __init__(self, config: ClutchConfig | None = None) -> None:
        self.config = config or ClutchConfig()
        self._cli_ok = False

    def _repo(self) -> Path | None:
        if not self.config.repo_path:
            return None
        repo = Path(self.config.repo_path).expanduser()
        return repo if (repo / "clutch" / "cli.py").is_file() else None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            # Dateisystem-Check reicht (CLI-Start dauert; Vertrag: probe < 2s)
            if self._repo() is not None:
                self._cli_ok = True
                caps |= {Capability.MODELS_LOCAL, Capability.MODELS_API,
                         Capability.ROUTING_STATS}
        except Exception:  # noqa: BLE001 — probe wirft nie
            self._cli_ok = False
        return caps

    def health(self) -> HealthInfo:
        if self._cli_ok:
            return HealthInfo("ok", f"CLI via {self._repo()}")
        return HealthInfo("offline", "clutch-Repo nicht gefunden (repo_path pruefen)")

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------
    def _cli(self, args: list[str]):
        repo = self._repo()
        if repo is None:
            raise AdapterError("clutch_missing", str(self.config.repo_path))
        cmd = [self.config.python_exe or sys.executable, "-m", "clutch.cli", *args]
        try:
            result = subprocess.run(
                cmd, cwd=str(repo), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.config.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterError("clutch_timeout", " ".join(args)) from exc
        output = (result.stdout or "").strip()
        if result.returncode != 0:
            raise AdapterError("clutch_failed",
                               (result.stderr or output or "").strip()[:300])
        start = output.find("[") if output.lstrip().startswith("[") or "[" in output[:5] else output.find("{")
        if start == -1:
            raise AdapterError("clutch_no_json", output[:200])
        try:
            return json.loads(output[start:])
        except json.JSONDecodeError as exc:
            raise AdapterError("clutch_bad_json", output[:200]) from exc

    # ------------------------------------------------------------------
    # ModelProvider / Routing
    # ------------------------------------------------------------------
    def models(self) -> list[dict]:
        data = self._cli(["models", "--json"])
        models = data if isinstance(data, list) else data.get("models", [])
        return [{
            "name": m.get("name"),
            "provider": m.get("provider"),
            "tier": m.get("gang_stufe"),
            "class": m.get("leistung"),
            "cost_in_1k": m.get("kosten_input_1k_usd"),
            "cost_out_1k": m.get("kosten_output_1k_usd"),
            "strengths": m.get("staerken", []),
            "source": "clutch",
        } for m in models]

    def stats(self):
        return self._cli(["stats", "--json"])

    def route_preview(self, task: str):
        return self._cli(["route", task, "--json"])
