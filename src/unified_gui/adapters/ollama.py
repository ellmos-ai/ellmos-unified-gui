# SPDX-License-Identifier: MIT
"""Ollama-Adapter: lokale Modelle direkt vom Ollama-Daemon (:11434).

Ergaenzt clutch (das Ollama-Modelle als Gears kennt) um die Live-Sicht:
was ist WIRKLICH gepullt/geladen. Reine Read-Anbindung.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from ..capabilities import Capability, HealthInfo
from ..config import OllamaConfig
from .base import AdapterError, BaseAdapter


class OllamaAdapter(BaseAdapter):
    name = "ollama"
    label = "Ollama (lokale Modelle)"

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()
        self._ok = False
        self._latency_ms: int | None = None
        self._version: str | None = None

    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            started = time.time()
            data = self._get("/api/version")
            self._version = data.get("version")
            self._latency_ms = int((time.time() - started) * 1000)
            self._ok = True
            caps.add(Capability.MODELS_LOCAL)
        except Exception:  # noqa: BLE001 — probe wirft nie
            self._ok = False
        return caps

    def health(self) -> HealthInfo:
        if self._ok:
            return HealthInfo("ok", self.config.url, version=self._version,
                              latency_ms=self._latency_ms)
        return HealthInfo("offline", f"Ollama nicht erreichbar ({self.config.url})")

    def _get(self, path: str):
        url = self.config.url.rstrip("/") + path
        try:
            with urllib.request.urlopen(url, timeout=self.config.timeout_s) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            raise AdapterError("ollama_unreachable", f"{url}: {exc}") from exc

    def models(self) -> list[dict]:
        data = self._get("/api/tags")
        result = []
        for m in data.get("models", []):
            size_gb = round((m.get("size") or 0) / (1024 ** 3), 1)
            details = m.get("details") or {}
            result.append({
                "name": m.get("name"),
                "provider": "ollama",
                "tier": None,
                "class": details.get("parameter_size"),
                "cost_in_1k": 0.0,
                "cost_out_1k": 0.0,
                "strengths": [f"{size_gb} GB", details.get("quantization_level") or ""],
                "source": "ollama",
            })
        return result

    def running(self) -> list[dict]:
        """Aktuell geladene Modelle (/api/ps)."""
        data = self._get("/api/ps")
        return data.get("models", [])
