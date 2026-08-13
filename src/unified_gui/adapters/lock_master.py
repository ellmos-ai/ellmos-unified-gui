# SPDX-License-Identifier: MIT
"""lock-master-Adapter: Permissions-Engine (LOCK.permissions.json) + Watcher-REST.

Zwei getrennt geprobte Teilfaehigkeiten:
- PERMISSIONS_RW: permissions.py aus dem lock-master-Repo importierbar UND
  mindestens ein Projekt-Root aufloesbar. Regeln werden direkt in den
  LOCK.permissions.json der Roots gelesen/geschrieben (Wahrheit bleibt dort).
- LOCKS_RW: lock-master-Watcher (Standard :8095) antwortet. Lock-Liste,
  Scan/Prune und Bulk-Lockdown laufen ueber dessen REST-API.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType

from ..capabilities import Capability, HealthInfo
from ..config import LockMasterConfig
from .base import AdapterError, BaseAdapter

PERMISSIONS_SKELETON = {
    "format": "lock-permissions-v1",
    "scope": "project",
    "owner": "user",
    "default": "allow",
    "rules": {"allow": [], "deny": [], "ask": []},
    "applies_to_agents": ["*"],
}

_MODULE_CANDIDATES = (
    # Korrekter ControlRoom-Stack-Pfad; Fallback auf persoenliche Scripts.
    "~/OneDrive/.TOPICS/.AI/.MODULES/.CONTROL/lock-master",
    "~/OneDrive/.TOPICS/.AI/.MODULES/lock-master",
    "~/OneDrive/_scripts",
)


class LockMasterAdapter(BaseAdapter):
    name = "lock-master"
    label = "lock-master (Locks & Berechtigungen)"

    def __init__(self, config: LockMasterConfig | None = None) -> None:
        self.config = config or LockMasterConfig()
        self._engine: ModuleType | None = None
        self._engine_error: str | None = None
        self._watcher_ok = False
        self._watcher_latency_ms: int | None = None

    # ------------------------------------------------------------------
    # Vertrag
    # ------------------------------------------------------------------
    def probe(self) -> set[Capability]:
        caps: set[Capability] = set()
        try:
            if self._load_engine() is not None and self.roots():
                caps.add(Capability.PERMISSIONS_RW)
        except Exception:  # noqa: BLE001 — probe wirft nie
            pass
        try:
            self._watcher_ok = self._probe_watcher()
            if self._watcher_ok:
                caps.add(Capability.LOCKS_RW)
        except Exception:  # noqa: BLE001
            self._watcher_ok = False
        return caps

    def health(self) -> HealthInfo:
        engine = self._engine is not None
        if engine and self._watcher_ok:
            return HealthInfo("ok", "Engine + Watcher", latency_ms=self._watcher_latency_ms)
        if engine:
            return HealthInfo("degraded", "Watcher nicht erreichbar (Locks read-only ueber Engine nicht verfuegbar)")
        if self._watcher_ok:
            return HealthInfo("degraded", f"permissions.py nicht importierbar ({self._engine_error or 'Pfad fehlt'})")
        return HealthInfo("offline", self._engine_error or "weder Engine noch Watcher gefunden")

    # ------------------------------------------------------------------
    # Engine (permissions.py) — dynamischer Import aus dem lock-master-Repo
    # ------------------------------------------------------------------
    def _module_candidates(self) -> list[Path]:
        candidates: list[Path] = []
        if self.config.module_path:
            candidates.append(Path(self.config.module_path).expanduser())
        candidates.extend(Path(p).expanduser() for p in _MODULE_CANDIDATES)
        return candidates

    def _load_engine(self) -> ModuleType | None:
        if self._engine is not None:
            return self._engine
        for base in self._module_candidates():
            path = base / "permissions.py"
            if not path.is_file():
                continue
            try:
                spec = importlib.util.spec_from_file_location("_lockmaster_permissions", path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # lock-masters permissions.py ist seit der Stack-Zerlegung
                # (2026-07-26) ein selbstersetzender Shim: er laedt das reale
                # Modul und setzt es unter sys.modules[<geladener Name>].
                # Unsere lokale Variable zeigt dann noch auf die Shim-Huelle —
                # deshalb das ersetzte Modul aus sys.modules bevorzugen.
                module = sys.modules.get(spec.name, module)
                self._engine = module
                self._engine_error = None
                return module
            except Exception as exc:  # noqa: BLE001
                self._engine_error = f"{type(exc).__name__}: {exc}"
        if self._engine_error is None:
            self._engine_error = "permissions.py in keinem Kandidatenpfad gefunden"
        return None

    # ------------------------------------------------------------------
    # Roots
    # ------------------------------------------------------------------
    def roots(self) -> list[Path]:
        """Projekt-Roots, in denen LOCK.permissions.json verwaltet wird."""
        roots: list[Path] = []
        for entry in self.config.roots:
            path = Path(os.path.expandvars(entry)).expanduser()
            if path.is_dir():
                roots.append(path)
        if roots:
            return roots
        if self.config.roots_file:
            roots_file = Path(os.path.expandvars(self.config.roots_file)).expanduser()
            if roots_file.is_file():
                try:
                    data = json.loads(roots_file.read_text(encoding="utf-8"))
                    for item in data.get("roots", []):
                        raw = item.get("path") if isinstance(item, dict) else item
                        if not raw:
                            continue
                        path = Path(os.path.expandvars(str(raw))).expanduser()
                        if path.is_dir():
                            roots.append(path)
                except (OSError, json.JSONDecodeError):
                    pass
        return roots

    def _resolve_root(self, root: str) -> Path:
        wanted = Path(os.path.expandvars(root)).expanduser()
        for known in self.roots():
            if known == wanted:
                return known
        raise AdapterError("unknown_root", f"Root nicht konfiguriert: {root}")

    # ------------------------------------------------------------------
    # PermissionStore
    # ------------------------------------------------------------------
    def rules(self, root: str) -> dict:
        engine = self._load_engine()
        if engine is None:
            raise AdapterError("engine_missing", self._engine_error or "")
        path = self._resolve_root(root)
        perm = engine.load_permissions(path)
        if perm is None:
            perm = json.loads(json.dumps(PERMISSIONS_SKELETON))
            perm["_exists"] = False
        else:
            perm["_exists"] = True
        perm.setdefault("rules", {"allow": [], "deny": [], "ask": []})
        for decision in ("allow", "deny", "ask"):
            perm["rules"].setdefault(decision, [])
        return perm

    def save_rules(self, root: str, perm: dict) -> None:
        path = self._resolve_root(root)
        clean = {k: v for k, v in perm.items() if not k.startswith("_")}
        clean.setdefault("format", "lock-permissions-v1")
        rules = clean.get("rules") or {}
        for decision in ("allow", "deny", "ask"):
            rules[decision] = [str(r).strip() for r in rules.get(decision, []) if str(r).strip()]
        clean["rules"] = rules
        if clean.get("default") not in ("allow", "deny", "ask"):
            raise AdapterError("invalid_default", "default muss allow|deny|ask sein")
        target = path / "LOCK.permissions.json"
        # Atomar schreiben (OneDrive-vertraeglich: temp im selben Ordner + replace)
        fd, tmp_name = tempfile.mkstemp(prefix=".lockperm-", suffix=".tmp", dir=str(path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(clean, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, target)
        except OSError as exc:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise AdapterError("write_failed", str(exc)) from exc

    def add_rule(self, root: str, decision: str, pattern: str, agents: list[str] | None = None) -> dict:
        if decision not in ("allow", "deny", "ask"):
            raise AdapterError("invalid_decision", decision)
        pattern = pattern.strip()
        if not pattern:
            raise AdapterError("empty_pattern", "Pattern darf nicht leer sein")
        perm = self.rules(root)
        if pattern not in perm["rules"][decision]:
            perm["rules"][decision].append(pattern)
        if agents:
            perm["applies_to_agents"] = agents
        self.save_rules(root, perm)
        return self.rules(root)

    def remove_rule(self, root: str, decision: str, pattern: str) -> dict:
        perm = self.rules(root)
        try:
            perm["rules"][decision].remove(pattern)
        except (KeyError, ValueError) as exc:
            raise AdapterError("rule_not_found", f"{decision}: {pattern}") from exc
        self.save_rules(root, perm)
        return self.rules(root)

    def set_default(self, root: str, default: str) -> dict:
        perm = self.rules(root)
        perm["default"] = default
        self.save_rules(root, perm)
        return self.rules(root)

    def evaluate(self, root: str, agent: str, action: str) -> str:
        engine = self._load_engine()
        if engine is None:
            raise AdapterError("engine_missing", self._engine_error or "")
        perm = self.rules(root)
        return engine.evaluate(perm, agent, action)

    # ------------------------------------------------------------------
    # LockControl (Watcher-REST)
    # ------------------------------------------------------------------
    def _probe_watcher(self) -> bool:
        started = time.time()
        try:
            self._watcher_get("/api/locks")
        except AdapterError:
            return False
        self._watcher_latency_ms = int((time.time() - started) * 1000)
        return True

    def _watcher_request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
        url = self.config.watcher_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Origin", self.config.watcher_url.rstrip("/"))
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_s) as response:
                body = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise AdapterError("watcher_unreachable", f"{url}: {exc}") from exc
        try:
            return json.loads(body) if body.strip() else {}
        except json.JSONDecodeError as exc:
            raise AdapterError("watcher_bad_response", body[:200]) from exc

    def _watcher_get(self, path: str) -> dict | list:
        return self._watcher_request(path)

    def locks(self) -> dict | list:
        return self._watcher_get("/api/locks")

    def scan(self) -> dict | list:
        return self._watcher_request("/api/scan", method="POST", payload={})

    def prune(self) -> dict | list:
        return self._watcher_request("/api/prune", method="POST", payload={})

    def bulk_lock(self, reason: str = "Unified GUI Lockdown") -> dict | list:
        return self._watcher_request("/api/bulk-lock", method="POST", payload={"reason": reason})

    def bulk_unlock(self) -> dict | list:
        return self._watcher_request("/api/bulk-unlock", method="POST", payload={})
