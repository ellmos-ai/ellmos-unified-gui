# SPDX-License-Identifier: MIT
"""ticket-master-Adapter: Intake/Queues/Move-Roundtrip + Score-Tiers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.ticket_master import (
    LEGACY_QUEUES,
    LIFECYCLE_QUEUES,
    QUEUES,
    TicketMasterAdapter,
)
from unified_gui.capabilities import Capability
from unified_gui.config import TicketMasterConfig


@pytest.fixture
def adapter(tmp_path):
    root = tmp_path / "TICKETS"
    root.mkdir()
    return TicketMasterAdapter(TicketMasterConfig(tickets_root=str(root)))


def test_probe(adapter):
    assert Capability.TICKETS_RW in adapter.probe()


def test_probe_missing_root():
    adapter = TicketMasterAdapter(TicketMasterConfig(tickets_root="/nonexistent"))
    assert adapter.probe() == set()


def test_intake_and_queues(adapter):
    info = adapter.intake("GUI zeigt 500 beim Speichern", "Repro: ...", priority="high")
    assert info["id"].startswith("T-")
    assert info["queue"] == "INBOX"
    assert info["title"] == "GUI zeigt 500 beim Speichern"

    queues = adapter.queues()
    assert len(queues["INBOX"]) == 1
    assert queues["QUEUED"] == []


def test_intake_ids_increment(adapter):
    first = adapter.intake("Eins", "")
    second = adapter.intake("Zwei", "")
    assert first["id"] != second["id"]
    assert second["id"].endswith("-02")


def test_move_roundtrip(adapter):
    ticket_id = adapter.intake("Move mich", "")["id"]
    moved = adapter.move(ticket_id, "QUEUED")
    assert moved["queue"] == "QUEUED"
    queues = adapter.queues()
    assert queues["INBOX"] == []
    assert queues["QUEUED"][0]["id"] == ticket_id

    back = adapter.move(ticket_id, "SOLVED")
    assert back["queue"] == "SOLVED"


def test_move_visits_every_v1_lifecycle_cluster(adapter):
    """Regression for T-20260825-608373032: move() must reach every v1
    cluster, not just the pre-v1 subset (QUEUED/PENDING/SOLVED/.USER)."""
    ticket_id = adapter.intake("Wandert durch alle Cluster", "")["id"]
    for target in ("ACTIONABLE", "BLOCKED", "WAITING", "USER", "PARKED", "QUEUED", "SOLVED"):
        moved = adapter.move(ticket_id, target)
        assert moved["queue"] == target
        queues = adapter.queues()
        assert queues[target][0]["id"] == ticket_id
        for other in LIFECYCLE_QUEUES:
            if other != target:
                assert queues[other] == []


def test_move_rejects_legacy_targets(adapter):
    """PENDING/.USER are read-only legacy per docs/CATEGORIES.de.md
    ("keine neuen Eintraege") -- they must stay valid *sources* to migrate
    out of, but invalid *targets* to move new tickets into."""
    ticket_id = adapter.intake("Darf nicht nach PENDING", "")["id"]
    for legacy in LEGACY_QUEUES:
        with pytest.raises(AdapterError):
            adapter.move(ticket_id, legacy)


def test_move_migrates_ticket_out_of_legacy_pending(adapter, tmp_path):
    """The documented lifecycle explicitly wants PENDING content 'einmalig
    auf ACTIONABLE/USER/BLOCKED/WAITING/PARKED verteilt' -- move() must be
    able to find and relocate a ticket that is sitting in a legacy folder."""
    root = Path(adapter.config.tickets_root)
    (root / "PENDING").mkdir()
    (root / "PENDING" / "T-20260101-01.txt").write_text(
        "ID: T-20260101-01\nTITLE: Alte Karteileiche\nPRIORITY: low\n", encoding="utf-8")
    moved = adapter.move("T-20260101-01", "ACTIONABLE")
    assert moved["queue"] == "ACTIONABLE"
    queues = adapter.queues()
    assert queues["PENDING"] == []
    assert queues["ACTIONABLE"][0]["id"] == "T-20260101-01"


def test_queues_reads_both_root_loose_files_and_inbox_subfolder(adapter):
    """INBOX has two physical sources (root is docs/CATEGORIES.de.md's
    documented alias, plus the real INBOX/ subfolder) -- both must surface
    in the same 'INBOX' bucket, not just one of them."""
    root = Path(adapter.config.tickets_root)
    loose_id = adapter.intake("Lose im Root", "")["id"]
    (root / "INBOX").mkdir()
    (root / "INBOX" / "T-20260101-02.txt").write_text(
        "ID: T-20260101-02\nTITLE: Im Unterordner\nPRIORITY: low\n", encoding="utf-8")
    queues = adapter.queues()
    inbox_ids = {t["id"] for t in queues["INBOX"]}
    assert inbox_ids == {loose_id, "T-20260101-02"}


def test_queues_tuple_matches_ticket_master_canonical_categories():
    """Drift guard for the exact bug this ticket fixes: QUEUES silently
    falling behind ticket-master's own categories-v1 contract. Compares
    against ticket-master's machine-readable source of truth
    (lib/ticket_writer.py LIFECYCLE_SUBCATEGORIES / _LEGACY_LIFECYCLE_CLUSTERS)
    when a local ticket-master checkout is importable, so the NEXT
    convention change fails this test instead of silently swallowing
    tickets again."""
    # Established sibling-repo pattern in this test suite (see
    # test_compare_race_adapter.py / test_skills_catalog_adapter.py):
    # resolve relative to this repo's own clone location, not $HOME --
    # both live under the same _Local_DEV/repos/ parent regardless of host.
    tm_path = Path(__file__).parent.parent.parent / "ticket-master"
    if not tm_path.is_dir():
        pytest.skip("no local ticket-master checkout to compare against")
    sys.path.insert(0, str(tm_path))
    try:
        from lib.ticket_writer import (
            LIFECYCLE_SUBCATEGORIES,
            _LEGACY_LIFECYCLE_CLUSTERS,
        )
    except ImportError:
        pytest.skip("ticket-master checkout present but lib.ticket_writer not importable")
    finally:
        sys.path.remove(str(tm_path))

    assert set(LIFECYCLE_QUEUES) == set(LIFECYCLE_SUBCATEGORIES.keys())
    # ticket-master's legacy set also lists "OPEN" (a name that was never a
    # real folder); this adapter has no "OPEN" concept left at all, it folds
    # into INBOX -- so the adapter's legacy set is the canonical legacy set
    # minus "OPEN".
    assert set(LEGACY_QUEUES) == _LEGACY_LIFECYCLE_CLUSTERS - {"OPEN"}
    assert set(QUEUES) == set(LIFECYCLE_QUEUES) | set(LEGACY_QUEUES)


def test_move_unknown_ticket(adapter):
    with pytest.raises(AdapterError):
        adapter.move("T-19990101-99", "QUEUED")


def test_claimed_ticket_parsing(adapter, tmp_path):
    root = Path(adapter.config.tickets_root)
    (root / "QUEUED").mkdir()
    (root / "QUEUED" / "T-20260101-01.LAPTOP.txt").write_text(
        "ID: T-20260101-01\nTITLE: Fremdes Ticket\nPRIORITY: low\n", encoding="utf-8")
    queues = adapter.queues()
    ticket = queues["QUEUED"][0]
    assert ticket["claimed_by"] == "LAPTOP"
    assert ticket["title"] == "Fremdes Ticket"


def test_score_tiers(adapter):
    # Fallback-Schwellen: tier1<=8, tier2<=12, tier3<=28, tier4>=29
    easy = adapter.score_preview(clarity=10, complexity=2, creativity=0, context=1, criticality=0)
    assert (easy.score, easy.tier) == (3, 1)

    hard = adapter.score_preview(clarity=2, complexity=9, creativity=8, context=9, criticality=9)
    assert hard.score == 43
    assert hard.tier == 4
    assert hard.advisor is True  # >= 35

    mid = adapter.score_preview(clarity=5, complexity=5, creativity=2, context=5, criticality=3)
    assert mid.tier == 3
    assert mid.advisor is False


def test_score_input_validation(adapter):
    with pytest.raises(AdapterError):
        adapter.score_preview(clarity=11, complexity=0, creativity=0, context=0, criticality=0)
