# SPDX-License-Identifier: MIT
"""lock-master-Adapter: Regel-Roundtrip + evaluate gegen die echte Engine.

Nutzt permissions.py aus dem Geschwister-Repo ../lock-master; wenn das auf
diesem System fehlt, werden die Engine-Tests uebersprungen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.lock_master import LockMasterAdapter
from unified_gui.capabilities import Capability
from unified_gui.config import LockMasterConfig

LOCK_MASTER_DIR = Path(__file__).parent.parent.parent / "lock-master"

pytestmark = pytest.mark.skipif(
    not (LOCK_MASTER_DIR / "permissions.py").is_file(),
    reason="lock-master (permissions.py) nicht vorhanden",
)


@pytest.fixture
def adapter(tmp_path):
    root = tmp_path / "projekt"
    root.mkdir()
    return LockMasterAdapter(LockMasterConfig(
        module_path=str(LOCK_MASTER_DIR),
        roots=[str(root)],
        watcher_url="http://127.0.0.1:1",  # absichtlich tot: LOCKS_RW soll fehlen
        timeout_s=0.2,
    ))


def test_probe_permissions_only(adapter):
    caps = adapter.probe()
    assert Capability.PERMISSIONS_RW in caps
    assert Capability.LOCKS_RW not in caps


def test_rules_skeleton_and_roundtrip(adapter):
    root = adapter.roots()[0]
    perm = adapter.rules(str(root))
    assert perm["_exists"] is False
    assert perm["default"] == "allow"

    adapter.add_rule(str(root), "deny", "Bash(rm:*)")
    adapter.add_rule(str(root), "ask", "Write(**)")
    perm = adapter.rules(str(root))
    assert perm["_exists"] is True
    assert "Bash(rm:*)" in perm["rules"]["deny"]

    # Datei ist echtes lock-master-Format (von der Engine ladbar)
    assert (root / "LOCK.permissions.json").is_file()


def test_evaluate_precedence(adapter):
    root = str(adapter.roots()[0])
    adapter.add_rule(root, "deny", "Bash(rm:*)")
    adapter.add_rule(root, "ask", "Write(**)")

    assert adapter.evaluate(root, "claude", "Bash(rm -rf x)") == "deny"
    assert adapter.evaluate(root, "claude", "Write(a.txt)") == "ask"
    assert adapter.evaluate(root, "claude", "Read(a.txt)") == "allow"  # default


def test_remove_rule_and_default(adapter):
    root = str(adapter.roots()[0])
    adapter.add_rule(root, "deny", "WebSearch")
    adapter.remove_rule(root, "deny", "WebSearch")
    assert adapter.rules(root)["rules"]["deny"] == []

    adapter.set_default(root, "ask")
    assert adapter.evaluate(root, "claude", "Read(x)") == "ask"

    with pytest.raises(AdapterError):
        adapter.set_default(root, "kaputt")


def test_unknown_root_rejected(adapter):
    with pytest.raises(AdapterError):
        adapter.rules("/woanders")
