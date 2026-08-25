# SPDX-License-Identifier: MIT
"""ellmos-chat-Adapter: backend-agnostische Chat-Runtime als optionaler
chat.runtime-Provider (Wheelhouse M1, T-20260825-835413946).

ellmos-chat liegt als Staging-Modul in OneDrive (.AI/.MODULES/.RUNTIME/
ellmos-chat, ellmos-module.v2.json: status=staging, ownership=external) --
kein pip-Paket, keine eigene .git. Sein Manifest deklariert
provides=[chat.runtime, runtime.model-backend, runtime.tool-registry]
bereits (verifiziert: backend.py/runtime.py/tools.py sind echte, lauffaehige
Chat-Runtime-Module -- kein Blindeintrag wie beim frueheren
unified-gui.host-Fund).

Konsum ueber sys.path-Erweiterung um <module_path>/src + regulaerer
Paket-Import -- exakt das Muster aus adapters/compare_race.py (dort
begruendet: das Zielmodul hat interne relative Imports zwischen mehreren
Dateien, ein importlib.spec_from_file_location auf eine einzelne Datei
scheitert daran; bei ellmos_chat gilt dasselbe fuer __init__.py, das
backend/runtime/security/store/tools zusammenfuehrt). Ob ellmos-chat spaeter
als eigenes Plan-D-Repo "gehoben" wird, aendert an diesem Adapter nichts --
module_path zeigt dann einfach auf den neuen Klon.

Bewusst NUR EIN Aufrufpfad angebunden: ask(text, chat_id) fragt die Runtime
einmalig und gibt die Antwort zurueck (v1-Durchstich laut Ticket-Scope --
"klein, lesender Durchstich reicht als v1; KEIN Vollausbau"). Keine
Session-/Verlaufsverwaltung im Panel (ellmos-chat haelt seinen eigenen
SQLiteChatStore selbst), kein Modellwechsel, kein Tool-Konfigurator --
SafetyPolicy-Default bleibt Mode.SAFE (ellmos_chat.security).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from ..capabilities import Capability, HealthInfo
from ..config import EllmosChatConfig
from .base import AdapterError, BaseAdapter


class EllmosChatAdapter(BaseAdapter):
    name = "ellmos-chat"
    label = "ellmos-chat (Chat-Runtime, staging)"

    def __init__(self, config: EllmosChatConfig | None = None) -> None:
        self.config = config or EllmosChatConfig()
        self._module: ModuleType | None = None
        self._runtime = None  # lazy: eine ChatRuntime pro Adapter-Instanz/Backend

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def _module_dir(self) -> Path | None:
        if not self.config.module_path:
            return None
        path = Path(self.config.module_path).expanduser()
        marker = path / "src" / "ellmos_chat" / "__init__.py"
        return path if marker.is_file() else None

    def probe(self) -> set[Capability]:
        try:
            ready = self._module_dir() is not None and self._ellmos_chat() is not None
        except Exception:  # noqa: BLE001 -- probe wirft nie (ADAPTER-CONTRACT.md §1)
            ready = False
        return {Capability.CHAT_RUNTIME} if ready else set()

    def health(self) -> HealthInfo:
        module_dir = self._module_dir()
        if module_dir is None:
            return HealthInfo("offline", f"module_path nicht gefunden: {self.config.module_path}")
        try:
            self._ellmos_chat()
        except Exception as exc:  # noqa: BLE001 -- Health darf nie werfen
            return HealthInfo("offline", f"{type(exc).__name__}: {exc}")
        return HealthInfo("ok", f"{module_dir} (backend={self.config.backend_type})")

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------
    def _ellmos_chat(self) -> ModuleType:
        if self._module is None:
            module_dir = self._module_dir()
            if module_dir is None:
                raise AdapterError("ellmos_chat_missing", "module_path nicht konfiguriert oder Modul fehlt")
            src = str(module_dir / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            self._module = importlib.import_module("ellmos_chat")
        return self._module

    def _get_runtime(self):
        if self._runtime is None:
            mod = self._ellmos_chat()
            backend = mod.create_backend({
                "type": self.config.backend_type,
                "default_model": self.config.default_model,
            })
            self._runtime = mod.ChatRuntime(backend, system_prompt="")
        return self._runtime

    # ------------------------------------------------------------------
    # Lesender Durchstich (v1)
    # ------------------------------------------------------------------
    async def ask(self, text: str, chat_id: str = "unified-gui") -> dict[str, Any]:
        """Eine Frage an die konfigurierte Chat-Runtime, eine Antwort zurueck.
        Kein Verlauf im Panel selbst -- ellmos-chat persistiert intern ueber
        seinen eigenen ChatStore (chat_id gruppiert dort den Verlauf)."""
        if not text or not text.strip():
            raise AdapterError("ellmos_chat_empty_text", "text darf nicht leer sein")
        try:
            runtime = self._get_runtime()
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001 -- fachlicher Fehler statt 500
            raise AdapterError("ellmos_chat_backend_error", f"{type(exc).__name__}: {exc}") from exc
        try:
            answer = await runtime.process(text, chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001 -- ChatRuntime.process() degradiert
            # bereits selbst auf Backend-Fehlertext; dieser Fang deckt nur
            # Programmierfehler/Timeouts der Runtime-Schicht selbst ab.
            raise AdapterError("ellmos_chat_process_failed", f"{type(exc).__name__}: {exc}") from exc
        return {"chat_id": chat_id, "answer": answer, "model": self.config.default_model}
