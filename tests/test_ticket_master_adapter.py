# SPDX-License-Identifier: MIT
"""ticket-master-Adapter: Intake/Queues/Move-Roundtrip + Score-Tiers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from unified_gui.adapters.base import AdapterError
from unified_gui.adapters.ticket_master import TicketMasterAdapter
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
    assert info["queue"] == "OPEN"
    assert info["title"] == "GUI zeigt 500 beim Speichern"

    queues = adapter.queues()
    assert len(queues["OPEN"]) == 1
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
    assert queues["OPEN"] == []
    assert queues["QUEUED"][0]["id"] == ticket_id

    back = adapter.move(ticket_id, "SOLVED")
    assert back["queue"] == "SOLVED"


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
