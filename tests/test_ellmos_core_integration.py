# SPDX-License-Identifier: MIT
"""End-zu-Ende: unified_gui.mount() in einem ECHTEN ellmos-core-Prozess --
kein Fake-Auth-Double (siehe test_host_auth_adapter.py, test_p5_role_gating.py,
test_p2_role_gating.py), sondern das reale Login/Session/RBAC von ellmos-core.

Beweist die reale Mount-Verdrahtung: ein Nutzer loggt sich bei ellmos-core ein,
die Rolle aus GENAU DIESER Session entscheidet, ob P5/P2-Schreibpfade in der
eingehaengten Konsole erlaubt sind -- ohne zweites Login, ohne zweite
Nutzerverwaltung. Ergaenzt (ersetzt nicht) die Fake-Adapter-Tests: die pruefen
den Adapter-Vertrag isoliert und schnell, dieser Test prueft, dass der reale
Host das auch tatsaechlich erfuellt.

Setzt voraus, dass die Geschwister-Repos ellmos-core und lock-master im
gleichen Klon-Wurzelordner (C:/_Local_DEV/repos/) liegen -- wie alle
Cross-Repo-Tests dieser Suite (siehe test_p5_role_gating.py). Fehlt eines,
wird sauber uebersprungen statt zu bloed zu failen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPOS_ROOT = Path(__file__).resolve().parent.parent.parent
_ELLMOS_CORE_SRC = _REPOS_ROOT / "ellmos-core" / "src"
_LOCK_MASTER_DIR = _REPOS_ROOT / "lock-master"

pytestmark = pytest.mark.skipif(
    not (_ELLMOS_CORE_SRC / "ellmos_core" / "app.py").is_file()
    or not (_LOCK_MASTER_DIR / "permissions.py").is_file(),
    reason="ellmos-core und/oder lock-master (Geschwister-Repos) nicht vorhanden",
)

# WICHTIG: `ellmos-core/src` wird bewusst NICHT hier auf Modulebene auf
# sys.path gelegt (anders als der unified_gui-eigene src-Pfad unten, der
# harmlos/idempotent ist). Ein Modulebene-Insert liefe waehrend der
# Kollektionsphase, also BEVOR irgendein Test laeuft -- und wuerde
# `import ellmos_core` fuer die GESAMTE restliche Pytest-Session global
# verfuegbar machen, auch fuer Dateien wie test_degradation.py, die exakt
# das Gegenteil (Kapazitaeten IM LEEREN Zustand) pruefen. Deshalb geschieht
# der Insert erst in der Fixture unten -- zu Testausfuehrungszeit, nicht zur
# Kollektionszeit (siehe ADAPTER-CONTRACT.md §5 fuer denselben Degradations-
# Vertrag, den das hier nicht verletzen darf).
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _mount_config(tmp_path: Path, lock_root: Path) -> dict:
    """Dieselbe Struktur wie test_mount.py/test_p5_role_gating.py -- alle
    Fremdsysteme zeigen auf tmp_path/nicht-existente Ports, NICHTS beruehrt
    echte Projektdaten."""
    return {
        "lock_master": {
            "module_path": str(_LOCK_MASTER_DIR),
            "roots": [str(lock_root)],
            "roots_file": None,
            "watcher_url": "http://127.0.0.1:1",
            "timeout_s": 0.2,
        },
        "ticket_master": {"tickets_root": str(tmp_path / "TICKETS"), "config_dir": None},
        "bach": {"bach_root": None, "rest_url": "http://127.0.0.1:1", "rest_timeout_s": 0.2},
        "scanner_tasks": {"db_path": None, "tool_path": None},
        "clutch": {"repo_path": None},
        "ollama": {"url": "http://127.0.0.1:1", "timeout_s": 0.2},
        "controlcenter": {"repo_path": None},
    }


@pytest.fixture(scope="module")
def mounted_client(tmp_path_factory):
    """Ein echter ellmos-core-Prozess (isolierte tmp-DB) mit der Konsole unter
    /control eingehaengt -- einmal pro Testdatei aufgebaut (mount() ist ein
    Ein-mal-Vorgang auf dem Prozess-Singleton `ellmos_core.app.app`; ein
    zweiter mount() auf demselben Praefix wuerde vom Router ignoriert, weil
    die erste Registrierung gewinnt -- siehe Starlette-Routing)."""
    mp = pytest.MonkeyPatch()
    tmp_path = tmp_path_factory.mktemp("host_mount_e2e")

    # Erst hier, zur Ausfuehrungszeit dieser Fixture, auf sys.path legen
    # (siehe Kommentar oben am Modulkopf) -- mp.undo() entfernt es wieder.
    mp.syspath_prepend(str(_ELLMOS_CORE_SRC))

    from ellmos_core.config import settings as core_settings
    mp.setattr(core_settings, "debug", True)
    mp.setattr(core_settings, "secure_cookies", False)
    mp.setattr(core_settings, "db_path", tmp_path / "core.db")

    # Wie ellmos-core/tests/conftest.py: kein echtes Netz/LLM in Tests.
    from ellmos_core.services import rag_service
    mp.setattr(rag_service, "_embed", lambda text: None)
    from ellmos_core.routers import chat as core_chat
    mp.setattr(core_chat, "_get_runtime", lambda *a, **kw: None)

    from ellmos_core.db import init_db
    init_db()

    from ellmos_core.app import app as core_app

    import unified_gui
    lock_root = tmp_path / "lock-projekt"
    lock_root.mkdir()
    unified_gui.mount(core_app, prefix="/control", config=_mount_config(tmp_path, lock_root))

    from starlette.testclient import TestClient
    client = TestClient(core_app)
    yield client, lock_root

    # sys.modules-Bereinigung: `import ellmos_core` bleibt sonst fuer den
    # Rest des Pytest-Prozesses im Cache haengen, selbst nachdem mp.undo()
    # den sys.path-Eintrag wieder entfernt hat (Python "vergisst" ein
    # Modul nicht durch Pfad-Entfernung allein). Ohne diese Bereinigung
    # wuerden spaeter laufende Dateien wie test_host_auth_adapter.py, die
    # PRUEFEN wie der Adapter sich OHNE ellmos-core im Prozess verhaelt,
    # faelschlich ein "ellmos-core ist da" vorfinden -- derselbe
    # Degradations-Vertrag, den dieser Test selbst beweisen soll (siehe
    # Kommentar am Modulkopf), darf durch das eigene Aufraeumen nicht
    # kaputtgehen.
    for name in [n for n in sys.modules if n == "ellmos_core" or n.startswith("ellmos_core.")]:
        del sys.modules[name]
    mp.undo()


def _csrf(client, path: str = "/login") -> str:
    r = client.get(path)
    m = re.search(r'name="_csrf" value="([^"]+)"', r.text)
    assert m, f"Kein CSRF-Token auf {path}"
    return m.group(1)


def _create_user(username: str, password: str, role: str) -> None:
    from ellmos_core.auth import hash_password
    from ellmos_core.db import get_connection

    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, email, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            (username, f"{username}@example.com", hash_password(password), role),
        )
        conn.commit()
    finally:
        conn.close()


def _login(client, username: str, password: str) -> None:
    tok = _csrf(client)
    r = client.post(
        "/login",
        data={"username": username, "password": password, "_csrf": tok},
        follow_redirects=False,
    )
    assert r.status_code == 303, f"Login fehlgeschlagen: {r.status_code} {r.text[:200]}"


def test_console_reachable_under_real_host(mounted_client):
    client, _ = mounted_client
    r = client.get("/control/")
    assert r.status_code == 200
    # root_path-sichere Links (wie test_mount.py) -- Beweis, dass es wirklich
    # der ECHTE ellmos-core-Host ist, der hier mountet, kein Test-Stub.
    assert '/control/static/app.css' in r.text


def test_real_login_as_user_role_is_forbidden_from_p5_write(mounted_client):
    client, lock_root = mounted_client
    _create_user("angestellte-e2e", "pw123456", "user")
    _login(client, "angestellte-e2e", "pw123456")

    resp = client.post(
        "/control/api/p5/rules",
        json={"root": str(lock_root), "decision": "deny", "pattern": "Bash(rm:*)"},
    )
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]
    # Regel wurde NICHT geschrieben:
    from unified_gui.adapters.lock_master import LockMasterAdapter
    from unified_gui.config import LockMasterConfig
    adapter = LockMasterAdapter(LockMasterConfig(module_path=str(_LOCK_MASTER_DIR), roots=[str(lock_root)]))
    perm = adapter.rules(str(lock_root))
    assert "Bash(rm:*)" not in perm.get("rules", {}).get("deny", [])


def test_real_login_as_admin_role_may_write_p5_rule(mounted_client):
    client, lock_root = mounted_client
    _create_user("boss-e2e", "pw123456", "admin")
    _login(client, "boss-e2e", "pw123456")

    resp = client.post(
        "/control/api/p5/rules",
        json={"root": str(lock_root), "decision": "deny", "pattern": "Bash(git push:*)"},
    )
    assert resp.status_code == 200, resp.text

    from unified_gui.adapters.lock_master import LockMasterAdapter
    from unified_gui.config import LockMasterConfig
    adapter = LockMasterAdapter(LockMasterConfig(module_path=str(_LOCK_MASTER_DIR), roots=[str(lock_root)]))
    perm = adapter.rules(str(lock_root))
    assert "Bash(git push:*)" in perm.get("rules", {}).get("deny", [])


def test_logged_out_visitor_still_sees_open_write_semantics_unchanged(mounted_client):
    """Ohne Login (kein Cookie) bleibt das bisherige Verhalten erhalten -- der
    HostAuthAdapter liefert current_user()=None (kein Nutzer, keine Session),
    also KEIN neuer Zwang (siehe ADAPTER-CONTRACT.md §5 + host_auth.py).

    `mounted_client` als Fixture-Parameter erzwingt, dass der Mount bereits
    passiert ist, BEVOR dieser Testkoerper laeuft (Fixture-Dependency, nicht
    Dateireihenfolge) -- ein frischer TestClient auf demselben, schon
    gemounteten `core_app`-Objekt hat garantiert keine Session-Cookies und
    mutiert nicht den von den anderen Tests genutzten Client."""
    from starlette.testclient import TestClient

    from ellmos_core.app import app as core_app  # bereits gemountet, kein Re-Mount

    anon_client = TestClient(core_app)
    resp = anon_client.post(
        "/control/api/p5/rules",
        json={"root": "/nonexistent-root-not-in-roots-list", "decision": "deny", "pattern": "Bash(x:*)"},
    )
    # Kein 403 durch die Rollen-Gate (root ist ohnehin nicht in der Roots-Liste,
    # also erwarten wir hoechstens einen Fachfehler, NIE den Admin-403):
    assert resp.status_code != 403 or "admin" not in resp.json().get("detail", "")
