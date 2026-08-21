# SPDX-License-Identifier: MIT
"""P11 Skill-Wizard: Routing + Rollen-Gating (gleiches Muster wie
test_p5_role_gating.py/test_p2_role_gating.py) gegen ein Fake-Adapter-Doppel --
die echte Adapter-Logik (create/set_description/quality) hat ihre eigenen
Tests in test_skills_catalog_adapter.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI
from starlette.testclient import TestClient

from unified_gui.panels import p11_skill_wizard


class _FakeHostAuth:
    def __init__(self, user: dict | None) -> None:
        self._user = user

    def current_user(self, request):
        return self._user


class _FakeSkillsCatalogAdapter:
    def __init__(self) -> None:
        self.created: list[tuple] = []
        self.described: list[tuple] = []
        self.validated: list[str] = []

    def categories(self):
        return [{"name": "dev", "count": 3}]

    def create(self, name, category, skill_type):
        self.created.append((name, category, skill_type))
        return {"name": name, "category": category, "type": skill_type, "path": f"/fake/{name}/SKILL.md"}

    def set_description(self, name, category, description):
        self.described.append((name, category, description))
        return {"name": name, "category": category, "description": description}

    def quality(self, name):
        self.validated.append(name)
        return {"name": name, "quality_score": 5, "rating": "exzellent", "dimensions": {}, "exit_code": 0}


def _client_for(adapter, auth_adapter):
    app = FastAPI()
    spec = p11_skill_wizard.build(adapter, auth_adapter)
    app.include_router(spec.router)
    return TestClient(app)


def _create_payload():
    return {"name": "sample-skill", "category": "dev", "type": "skill"}


def test_guidance_is_ungated_and_reads_open():
    client = _client_for(_FakeSkillsCatalogAdapter(), _FakeHostAuth({"id": 2, "username": "u", "role": "user"}))
    resp = client.get("/api/p11/guidance")
    assert resp.status_code == 200
    assert "what" in resp.json() and "when" in resp.json()


def test_categories_is_ungated():
    client = _client_for(_FakeSkillsCatalogAdapter(), _FakeHostAuth({"id": 2, "username": "u", "role": "user"}))
    resp = client.get("/api/p11/categories")
    assert resp.status_code == 200
    assert resp.json() == [{"name": "dev", "count": 3}]


def test_no_auth_adapter_writes_unchanged():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, None)
    resp = client.post("/api/p11/create", json=_create_payload())
    assert resp.status_code == 200
    assert adapter.created == [("sample-skill", "dev", "skill")]


def test_no_session_writes_unchanged():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth(None))
    resp = client.post("/api/p11/create", json=_create_payload())
    assert resp.status_code == 200
    assert len(adapter.created) == 1


def test_non_admin_forbidden_from_create():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.post("/api/p11/create", json=_create_payload())
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]
    assert adapter.created == []


def test_admin_may_create():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"}))
    resp = client.post("/api/p11/create", json=_create_payload())
    assert resp.status_code == 200
    assert adapter.created == [("sample-skill", "dev", "skill")]


def test_non_admin_forbidden_from_describe():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.post("/api/p11/describe", json={
        "name": "sample-skill", "category": "dev", "what": "tut etwas", "when": "wenn X passiert",
    })
    assert resp.status_code == 403
    assert adapter.described == []


def test_admin_describe_combines_what_and_when():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"}))
    resp = client.post("/api/p11/describe", json={
        "name": "sample-skill", "category": "dev", "what": "Tut X.", "when": "Trigger bei Y.",
    })
    assert resp.status_code == 200
    assert adapter.described == [("sample-skill", "dev", "Tut X. Trigger bei Y.")]


def test_describe_rejects_empty_fields():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, None)
    resp = client.post("/api/p11/describe", json={
        "name": "sample-skill", "category": "dev", "what": "  ", "when": "etwas",
    })
    assert resp.status_code == 400
    assert adapter.described == []


def test_non_admin_forbidden_from_validate():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 2, "username": "angestellte", "role": "user"}))
    resp = client.post("/api/p11/validate", json={"name": "sample-skill"})
    assert resp.status_code == 403
    assert adapter.validated == []


def test_admin_may_validate():
    adapter = _FakeSkillsCatalogAdapter()
    client = _client_for(adapter, _FakeHostAuth({"id": 1, "username": "boss", "role": "admin"}))
    resp = client.post("/api/p11/validate", json={"name": "sample-skill"})
    assert resp.status_code == 200
    assert resp.json()["quality_score"] == 5
    assert adapter.validated == ["sample-skill"]
