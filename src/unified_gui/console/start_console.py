# SPDX-License-Identifier: MIT
"""Rollen aus Modulmanifesten in einer sichtbaren Konsole starten."""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from typing import Callable, Sequence

from ..adapters.base import AdapterError
from ..adapters.role_manifest import RoleEntry, RoleManifestAdapter

MANIFEST_ENV = "UNIFIED_GUI_ROLE_MANIFESTS"


@dataclass(frozen=True)
class LaunchPlan:
    command: tuple[str, ...]
    backend: str
    notices: tuple[str, ...] = ()


def _version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in value.split("."):
        digits = "".join(char for char in part if char.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _reconfigure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def _agent_launcher() -> str | None:
    executable = shutil.which("agent-launcher")
    if not executable:
        return None
    try:
        version = metadata.version("agent-launcher")
    except metadata.PackageNotFoundError:
        return None
    return executable if _version_tuple(version) >= (0, 2, 0) else None


def build_launch_plan(
    role: RoleEntry,
    *,
    provider: str,
    model: str = "",
    effort: str = "",
    request: str = "",
    workdir: str | Path | None = None,
    session_name: str = "",
    agent_launcher: str | None = None,
    taskplan_available: bool | None = None,
    coma_available: bool | None = None,
) -> LaunchPlan:
    """Wählt den höchsten vorhandenen Host und macht jeden Rückfall sichtbar."""
    provider = provider.strip().lower()
    if provider not in role.providers:
        raise ValueError(
            f"Provider {provider!r} ist für {role.key} nicht erlaubt: "
            f"{', '.join(role.providers)}"
        )
    if not role.prompt_file.is_file():
        raise ValueError(f"Prompt-Datei nicht gefunden: {role.prompt_file}")
    actual_request = request.strip() or role.request
    actual_workdir = Path(workdir).expanduser().resolve() if workdir else Path.cwd().resolve()
    if not actual_workdir.is_dir():
        raise ValueError(f"Arbeitsverzeichnis nicht gefunden: {actual_workdir}")
    name = session_name.strip() or role.key.replace(":", "-")

    host = _agent_launcher() if agent_launcher is None else agent_launcher
    if host:
        command = [
            host, "start", name,
            "--provider", provider,
            "--prompt-file", str(role.prompt_file),
            "--request", actual_request,
            "--cwd", str(actual_workdir),
            "--visible",
        ]
        if model:
            command.extend(["--model", model])
        if effort:
            command.extend(["--effort", effort])
        return LaunchPlan(tuple(command), "agent-launcher")

    notices = ["[FALLBACK] agent-launcher >= 0.2.0 fehlt; verwende den nächsten Startweg."]
    if taskplan_available is None:
        taskplan_available = importlib.util.find_spec("taskplan") is not None
    if taskplan_available:
        command = [
            sys.executable, "-m", "taskplan", "launch",
            "--label", role.key,
            "--prompt-file", str(role.prompt_file),
            "--request", actual_request,
            "--provider", provider,
        ]
        if model:
            command.extend(["--model", model])
        if effort:
            command.extend(["--effort", effort])
        return LaunchPlan(tuple(command), "taskplan", tuple(notices))

    notices.append("[FALLBACK] task-master fehlt; verwende COMA direkt.")
    if coma_available is None:
        coma_available = importlib.util.find_spec("coma.session") is not None
    if coma_available:
        command = [
            sys.executable, "-m", "coma", "session",
            "--provider", provider,
            "--prompt-file", str(role.prompt_file),
            "--request", actual_request,
            "--cwd", str(actual_workdir),
            "--mode", "interactive",
        ]
        if model:
            command.extend(["--model", model])
        if effort:
            command.extend(["--effort", effort])
        return LaunchPlan(tuple(command), "coma", tuple(notices))

    notices.append("[FALLBACK] COMA fehlt; verwende den modul-eigenen Starter.")
    if role.starter and role.starter.is_file():
        return LaunchPlan((str(role.starter),), "module-starter", tuple(notices))
    raise ValueError(
        "Kein Startweg verfügbar: agent-launcher, task-master und COMA fehlen; "
        f"kein vorhandener Starter für {role.key}."
    )


def spawn_window(command: Sequence[str], *, platform: str | None = None) -> subprocess.Popen:
    """Startet genau einen eigenen sichtbaren Konsolenprozess."""
    actual = platform or os.name
    if actual == "nt":
        return subprocess.Popen(list(command), creationflags=subprocess.CREATE_NEW_CONSOLE)
    terminal = next(
        (path for name in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm")
         if (path := shutil.which(name))),
        None,
    )
    if not terminal:
        raise OSError("Kein unterstütztes POSIX-Terminal gefunden")
    flag = "--" if Path(terminal).name in {"gnome-terminal", "konsole"} else "-e"
    return subprocess.Popen([terminal, flag, *command])


def select_role(roles: Sequence[RoleEntry], value: str) -> RoleEntry:
    wanted = value.strip().lower()
    if wanted.isdigit() and 1 <= int(wanted) <= len(roles):
        return roles[int(wanted) - 1]
    exact = [role for role in roles if wanted in {role.key.lower(), role.role_id.lower(), role.label.lower()}]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Rolle {value!r} ist mehrdeutig; verwende modul:rolle")
    raise ValueError(f"Unbekannte Rolle {value!r}")


def _manifest_paths(values: Sequence[str]) -> list[Path]:
    raw = list(values)
    if not raw:
        raw = [item for item in os.environ.get(MANIFEST_ENV, "").split(os.pathsep) if item]
    if not raw:
        candidate = Path.cwd() / "ellmos-module.v2.json"
        if candidate.is_file():
            raw = [str(candidate)]
    return [Path(value).expanduser().resolve() for value in raw]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m unified_gui.console")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="Modulrolle in einem Konsolenfenster starten")
    start.add_argument("role", nargs="?", help="Nummer, Rollen-ID oder modul:rolle")
    start.add_argument("--manifest", action="append", default=[], help="Modulmanifest oder künftiger Rollenkatalog")
    start.add_argument("--provider")
    start.add_argument("--model", default="")
    start.add_argument("--effort", default="")
    start.add_argument("--request", default="")
    start.add_argument("--cwd")
    start.add_argument("--name", default="")
    start.add_argument("--dry-run", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    spawn: Callable[[Sequence[str]], object] = spawn_window,
) -> int:
    _reconfigure_streams()
    args = build_parser().parse_args(argv)
    try:
        roles = RoleManifestAdapter(_manifest_paths(args.manifest)).roles()
        if not args.role:
            print("Verfügbare Modulrollen:")
            for index, role in enumerate(roles, 1):
                print(f"  [{index}] {role.key} — {role.label}")
            role_value = input_fn("Rolle (Nummer oder Name): ")
        else:
            role_value = args.role
        role = select_role(roles, role_value)

        provider = (args.provider or "").strip().lower()
        if not provider:
            print("Anbieter:")
            for index, name in enumerate(role.providers, 1):
                print(f"  [{index}] {name}")
            answer = input_fn(f"Anbieter [Enter = {role.providers[0]}]: ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(role.providers):
                provider = role.providers[int(answer) - 1]
            else:
                provider = answer.lower() or role.providers[0]

        plan = build_launch_plan(
            role,
            provider=provider,
            model=args.model,
            effort=args.effort,
            request=args.request,
            workdir=args.cwd,
            session_name=args.name,
        )
    except (AdapterError, ValueError) as exc:
        print(f"[FEHLER] {exc}", file=sys.stderr)
        return 2

    for notice in plan.notices:
        print(notice)
    print(f"[START] {role.key} über {plan.backend}")
    print(subprocess.list2cmdline(list(plan.command)))
    if args.dry_run:
        return 0
    try:
        process = spawn(plan.command)
    except OSError as exc:
        print(f"[FEHLER] Konsolenfenster nicht startbar: {exc}", file=sys.stderr)
        return 1
    pid = getattr(process, "pid", None)
    print(f"[START] PID {pid if pid is not None else 'unbekannt'}")
    return 0


__all__ = [
    "LaunchPlan", "build_launch_plan", "build_parser", "main", "select_role",
    "spawn_window",
]
