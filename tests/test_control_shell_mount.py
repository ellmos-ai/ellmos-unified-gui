"""Optional shared shell mount: no backend calls, per-app state and parity."""
import builtins
import importlib
import os
import sys

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from unified_gui import create_app, create_control_shell_app, mount_control_shell
from unified_gui.capabilities import CapabilityRegistry


def fake_renderer(branding=None, api_base=""):
    return f'<title>{(branding or {}).get("title", "neutral")}</title><p>{api_base}</p>'


def test_lite_does_not_import_full_shell_or_probe_in_test(monkeypatch):
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith(("ocean_gui_shell", "hub", "gui", "bach")):
            raise AssertionError("Lite attempted backend/full-shell import: " + name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(CapabilityRegistry, "_probe", lambda *args: None)
    app = create_app({"audit_log_path": "off"})
    assert app.state.registry.available == set()
    assert not any(getattr(route, "path", None) == "/activity" for route in app.routes)


def test_mount_redirect_and_per_instance_branding():
    host = FastAPI()
    mount_control_shell(host, "/one", branding={"title": "Eins"}, renderer=fake_renderer)
    mount_control_shell(host, "/two", branding={"title": "Zwei"}, renderer=fake_renderer)
    with TestClient(host) as client:
        assert client.get("/one/", follow_redirects=False).headers["location"] == "/one/activity"
        assert "Eins" in client.get("/one/activity").text
        assert "Zwei" not in client.get("/one/activity").text
        assert "Zwei" in client.get("/two/activity").text
        assert client.post("/one/activity").status_code == 405
        assert client.get("/").status_code == 404


def test_standalone_local_guard():
    app = create_control_shell_app(renderer=fake_renderer)
    with TestClient(app, client=("203.0.113.1", 1)) as client:
        assert client.get("/activity").status_code == 403


def test_rw_requires_explicit_backend():
    with pytest.raises(ValueError, match="explizite Control-API"):
        create_control_shell_app(read_only=False, renderer=fake_renderer)


@pytest.fixture
def neutral():
    # Explicit PYTHONPATH or an installed independent package, never discovery of BACH.
    return optional_consumer_module("ocean_gui_shell")


def optional_consumer_module(name):
    if os.environ.get("UNIFIED_GUI_REQUIRE_CONTROL_SHELL") == "1":
        return importlib.import_module(name)
    return pytest.importorskip(name)


@pytest.mark.parametrize("name", ["ocean_gui_shell", "gui.activity_dashboard"])
def test_required_consumer_missing_dependency_fails(monkeypatch, name):
    monkeypatch.setenv("UNIFIED_GUI_REQUIRE_CONTROL_SHELL", "1")

    def missing(module_name):
        raise ModuleNotFoundError(module_name)

    monkeypatch.setattr(importlib, "import_module", missing)
    monkeypatch.setattr(pytest, "importorskip", lambda *args: pytest.fail("required CI attempted skip"))
    with pytest.raises(ModuleNotFoundError, match=name):
        optional_consumer_module(name)


@pytest.mark.parametrize("name", ["ocean_gui_shell", "gui.activity_dashboard"])
def test_lite_keeps_explicit_optional_consumer(monkeypatch, name):
    monkeypatch.delenv("UNIFIED_GUI_REQUIRE_CONTROL_SHELL", raising=False)
    marker = object()
    monkeypatch.setattr(pytest, "importorskip", lambda module_name: marker if module_name == name else None)
    assert optional_consumer_module(name) is marker


def test_real_neutral_mount_standalone_parity(neutral):
    branding = {"title": "OCEAN Prüfung", "brand_name": "OCEAN", "nav_links": []}
    expected = neutral.render_activity_dashboard({**branding, "read_only": True}, "/backend/api")
    standalone = create_control_shell_app(control_api="/backend/api", branding=branding)
    host = FastAPI()
    mount_control_shell(host, "/control", control_api="/backend/api", branding=branding)
    with TestClient(standalone) as one, TestClient(host) as two:
        assert one.get("/activity").text == expected
        assert two.get("/control/activity").text == expected


def test_real_mount_navigation_and_rw_configuration(neutral):
    host = FastAPI()
    mount_control_shell(host, "/deck", control_api="/api", read_only=False)
    with TestClient(host) as client:
        page = client.get("/deck/activity").text
        assert 'href="/deck/"' in page
        assert '"readOnly": false' in page
        assert "checkControlAuth" in page


def test_real_bach_consumer_parity(neutral):
    bach = optional_consumer_module("gui.activity_dashboard")
    host = FastAPI()
    mount_control_shell(host, "/bach", branding=bach.DEFAULT_BRANDING,
                        control_api="/api", read_only=False)
    with TestClient(host) as client:
        assert client.get("/bach/activity").text == bach.render_activity_dashboard(api_base="/api")
    assert sys.modules["ocean_gui_shell"] is neutral
