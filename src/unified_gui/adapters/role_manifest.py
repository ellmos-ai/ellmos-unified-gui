# SPDX-License-Identifier: MIT
"""Read-only-Adapter fuer modul-eigene ``roles[]``-Manifeste."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..capabilities import Capability, HealthInfo
from .base import AdapterError, BaseAdapter


@dataclass(frozen=True)
class RoleEntry:
    module_id: str
    role_id: str
    label: str
    prompt_file: Path
    request: str
    providers: tuple[str, ...]
    modes: tuple[str, ...]
    starter: Path | None
    manifest_file: Path

    @property
    def key(self) -> str:
        return f"{self.module_id}:{self.role_id}"


class RoleManifestAdapter(BaseAdapter):
    """Projiziert vorhandene Rollen; schreibt und aggregiert nichts dauerhaft."""

    name = "role-manifest"
    label = "Modulrollen"

    def __init__(self, manifests: Iterable[str | Path]) -> None:
        self.manifests = tuple(Path(path).expanduser().resolve() for path in manifests)

    @staticmethod
    def _entries(path: Path) -> list[RoleEntry]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AdapterError("roles_manifest_invalid", f"{path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise AdapterError("roles_manifest_invalid", f"{path}: Objekt erwartet")

        modules = payload.get("modules")
        records: list[tuple[str, Path, object]] = []
        if isinstance(modules, list):
            for module in modules:
                if not isinstance(module, dict):
                    continue
                module_id = str(module.get("id") or "").strip()
                base = path.parent
                manifest_ref = module.get("manifest") or module.get("manifest_path")
                if manifest_ref:
                    base = (path.parent / str(manifest_ref)).resolve().parent
                records.append((module_id, base, module.get("roles")))
        else:
            records.append((str(payload.get("id") or "").strip(), path.parent, payload.get("roles")))

        result: list[RoleEntry] = []
        for module_id, base, roles in records:
            if not module_id or not isinstance(roles, list):
                continue
            for raw in roles:
                if not isinstance(raw, dict):
                    continue
                role_id = str(raw.get("id") or "").strip().lower()
                prompt = str(raw.get("prompt") or "").strip()
                request = str(raw.get("request") or "").strip()
                providers = tuple(str(value).strip().lower() for value in raw.get("providers", []) if str(value).strip())
                if not role_id or not prompt or not request or not providers:
                    continue
                prompt_file = (base / prompt).resolve()
                starter_raw = str(raw.get("starter") or "").strip()
                result.append(RoleEntry(
                    module_id=module_id,
                    role_id=role_id,
                    label=str(raw.get("label") or role_id).strip(),
                    prompt_file=prompt_file,
                    request=request,
                    providers=providers,
                    modes=tuple(str(value).strip() for value in raw.get("modes", []) if str(value).strip()),
                    starter=(base / starter_raw).resolve() if starter_raw else None,
                    manifest_file=path,
                ))
        return result

    def roles(self) -> list[RoleEntry]:
        if not self.manifests:
            raise AdapterError("roles_manifest_missing", "--manifest oder UNIFIED_GUI_ROLE_MANIFESTS fehlt")
        result: list[RoleEntry] = []
        seen: set[str] = set()
        for path in self.manifests:
            if not path.is_file():
                raise AdapterError("roles_manifest_missing", str(path))
            for role in self._entries(path):
                if role.key in seen:
                    raise AdapterError("roles_manifest_duplicate", role.key)
                seen.add(role.key)
                result.append(role)
        if not result:
            raise AdapterError("roles_empty", "Kein vollständiger roles[]-Eintrag gefunden")
        return result

    def probe(self) -> set[Capability]:
        try:
            self.roles()
        except AdapterError:
            return set()
        return {Capability.ROLES_CATALOG}

    def health(self) -> HealthInfo:
        try:
            count = len(self.roles())
        except AdapterError as exc:
            return HealthInfo(status="offline", detail=str(exc))
        return HealthInfo(status="ok", detail=f"{count} Modulrolle(n)")


__all__ = ["RoleEntry", "RoleManifestAdapter"]
