# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from unified_gui.adapters.role_manifest import RoleManifestAdapter
from unified_gui.capabilities import Capability
from unified_gui.console import start_console
from unified_gui.console.start_console import LaunchPlan, build_launch_plan, select_role


def _manifest(tmp_path: Path) -> Path:
    prompt = tmp_path / "prompts" / "Rolle ä.md"
    prompt.parent.mkdir()
    prompt.write_text("# Rolle\n", encoding="utf-8")
    path = tmp_path / "ellmos-module.v2.json"
    path.write_text(json.dumps({
        "schema": "ellmos.module.v2",
        "id": "example-module",
        "roles": [{
            "id": "reviewer",
            "label": "REVIEWER",
            "prompt": "prompts/Rolle ä.md",
            "request": "Prüfe vollständig.",
            "modes": ["normal"],
            "providers": ["claude", "codex"],
            "starter": "start.sh",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return path


def test_manifest_adapter_reads_roles_without_copying_prompts(tmp_path):
    adapter = RoleManifestAdapter([_manifest(tmp_path)])
    roles = adapter.roles()
    assert [role.key for role in roles] == ["example-module:reviewer"]
    assert roles[0].prompt_file.name == "Rolle ä.md"
    assert roles[0].request == "Prüfe vollständig."
    assert adapter.probe() == {Capability.ROLES_CATALOG}
    assert adapter.health().status == "ok"


def test_manifest_probe_degrades_without_throwing(tmp_path):
    adapter = RoleManifestAdapter([tmp_path / "missing.json"])
    assert adapter.probe() == set()
    assert adapter.health().status == "offline"


def test_future_catalog_modules_shape_is_already_consumable(tmp_path):
    module_root = tmp_path / "module"
    module_root.mkdir()
    (module_root / "PROMPT.md").write_text("# Role", encoding="utf-8")
    (module_root / "ellmos-module.v2.json").write_text("{}", encoding="utf-8")
    catalog = tmp_path / "roles.catalog.json"
    catalog.write_text(json.dumps({"modules": [{
        "id": "future",
        "manifest_path": "module/ellmos-module.v2.json",
        "roles": [{
            "id": "one", "prompt": "PROMPT.md", "request": "Go",
            "providers": ["codex"],
        }],
    }]}), encoding="utf-8")
    role = RoleManifestAdapter([catalog]).roles()[0]
    assert role.key == "future:one"
    assert role.prompt_file == (module_root / "PROMPT.md").resolve()


def test_role_selection_accepts_number_name_and_qualified_key(tmp_path):
    role = RoleManifestAdapter([_manifest(tmp_path)]).roles()[0]
    assert select_role([role], "1") is role
    assert select_role([role], "reviewer") is role
    assert select_role([role], "example-module:reviewer") is role
    with pytest.raises(ValueError, match="Unbekannte Rolle"):
        select_role([role], "missing")


def test_agent_launcher_02_is_preferred_and_receives_all_fields(tmp_path):
    role = RoleManifestAdapter([_manifest(tmp_path)]).roles()[0]
    plan = build_launch_plan(
        role,
        provider="codex",
        model="gpt-test",
        effort="high",
        workdir=tmp_path,
        agent_launcher="agent-launcher-test",
    )
    assert plan.backend == "agent-launcher"
    assert plan.command[:3] == ("agent-launcher-test", "start", "example-module-reviewer")
    assert plan.command[plan.command.index("--prompt-file") + 1] == str(role.prompt_file)
    assert plan.command[plan.command.index("--model") + 1] == "gpt-test"
    assert plan.command[plan.command.index("--effort") + 1] == "high"


def test_fallback_chain_is_visible_and_ordered(tmp_path):
    role = RoleManifestAdapter([_manifest(tmp_path)]).roles()[0]
    taskplan = build_launch_plan(
        role, provider="claude", workdir=tmp_path, agent_launcher="",
        taskplan_available=True,
    )
    assert taskplan.backend == "taskplan"
    assert taskplan.notices == (
        "[FALLBACK] agent-launcher >= 0.2.0 fehlt; verwende den nächsten Startweg.",
    )
    coma = build_launch_plan(
        role, provider="claude", workdir=tmp_path, agent_launcher="",
        taskplan_available=False, coma_available=True,
    )
    assert coma.backend == "coma"
    assert len(coma.notices) == 2
    with pytest.raises(ValueError, match="Kein Startweg"):
        build_launch_plan(
            role, provider="claude", workdir=tmp_path, agent_launcher="",
            taskplan_available=False, coma_available=False,
        )


def test_missing_prompt_and_invalid_provider_fail_before_spawn(tmp_path):
    role = RoleManifestAdapter([_manifest(tmp_path)]).roles()[0]
    role.prompt_file.unlink()
    with pytest.raises(ValueError, match="Prompt-Datei"):
        build_launch_plan(role, provider="claude", workdir=tmp_path)
    with pytest.raises(ValueError, match="nicht erlaubt"):
        build_launch_plan(role, provider="agy", workdir=tmp_path)


def test_cli_menu_accepts_number_and_dry_run_never_spawns(tmp_path, capsys):
    manifest = _manifest(tmp_path)
    fake_plan = LaunchPlan(("fake", "command"), "fake-host")
    with mock.patch.object(start_console, "build_launch_plan", return_value=fake_plan), \
            mock.patch.object(start_console, "_agent_launcher", return_value=None):
        spawned = mock.Mock()
        answers = iter(["1", "2"])
        code = start_console.main(
            ["start", "--manifest", str(manifest), "--dry-run"],
            input_fn=lambda _prompt: next(answers),
            spawn=spawned,
        )
    assert code == 0
    spawned.assert_not_called()
    output = capsys.readouterr().out
    assert "example-module:reviewer" in output
    assert "fake-host" in output


def test_spawn_window_uses_new_console_on_windows(monkeypatch):
    popen = mock.Mock(return_value=mock.Mock(pid=123))
    monkeypatch.setattr(start_console.subprocess, "Popen", popen)
    result = start_console.spawn_window(["fake", "arg"], platform="nt")
    assert result.pid == 123
    assert popen.call_args.kwargs["creationflags"] == start_console.subprocess.CREATE_NEW_CONSOLE
