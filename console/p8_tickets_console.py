# SPDX-License-Identifier: MIT
"""Wheelhouse Konsole-Spike (T-20260825-450296633): lesender Durchstich fuer P8
Tickets.

ZWECK: den zentralen Nachweis erbringen, den die ganze Wheelhouse-Roadmap
braucht -- derselbe Adapter (unified_gui.adapters.ticket_master.
TicketMasterAdapter), der P8s HTMX-Web-Panel speist (siehe
src/unified_gui/panels/p8_tickets.py, dort nur ein duenner FastAPI-Router um
denselben Adapter), kann OHNE Aenderung auch eine Terminal-Ausgabe speisen --
kein HTTP-Hop, kein zweiter Backend-Zugriff, nur ein zweiter (duenner)
Aufrufer desselben Python-Objekts. Das ist exakt die D03-Adapter-Disziplin
aus DECISIONS.md ("Panels nur ueber Adapter -- nie Backend-Direktzugriff"),
nur mit einem zweiten, terminal-basierten "Panel" statt eines Web-Panels.

Bewusst NICHT Teil dieses Spikes: Schreibpfade (intake/move/score), eine
vollstaendige CLI-Befehlsstruktur, Textual/Rich-Widgets. Nur der Lesepfad,
nur ein Panel -- der Nachweis soll klein und eindeutig bleiben.

Aufruf: python console/p8_tickets_console.py [--root <tickets-dir>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unified_gui.adapters.ticket_master import TicketMasterAdapter  # noqa: E402
from unified_gui.adapters.base import AdapterError  # noqa: E402
from unified_gui.config import TicketMasterConfig  # noqa: E402

DEFAULT_TICKETS_ROOT = r"C:\Users\User\OneDrive\.TOPICS\_control-center\_TICKETS"


def render_queues(queues: dict[str, list[dict]]) -> None:
    """Bewusst schlichter Text-Renderer (kein rich/Textual) -- der Spike prueft
    die Adapter-Wiederverwendung, nicht die Terminal-Aesthetik. Ein spaeterer
    Renderer-Wechsel (z.B. rich.table) aendert an dieser Funktion etwas,
    NICHT am Adapter-Aufruf darueber -- genau die Trennung, die der Spike
    zeigen soll."""
    total = 0
    for queue, tickets in queues.items():
        print(f"\n{queue} ({len(tickets)})")
        print("-" * (len(queue) + len(str(len(tickets))) + 3))
        for t in tickets:
            total += 1
            title = t.get("title") or t.get("id", "?")
            print(f"  {t.get('id', '?'):<28} {title[:60]}")
    print(f"\nGesamt: {total} Tickets ueber {len(queues)} Queues (Adapter: TicketMasterAdapter, kein HTTP-Hop).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=DEFAULT_TICKETS_ROOT, help="ticket-master Tickets-Wurzel")
    args = parser.parse_args(argv)

    # Derselbe Adapter-Typ, dieselbe Config-Klasse wie im Web-Panel (config.py,
    # panels/p8_tickets.py) -- nur die Instanziierung ist hier console-lokal,
    # weil der Web-Mount-Prozess (KONZEPT.md) nicht laeuft.
    adapter = TicketMasterAdapter(TicketMasterConfig(tickets_root=args.root))

    health = adapter.health()
    print(f"ticket-master: {health.status} -- {health.detail}")
    if health.status == "offline":
        print("Kein tickets_root konfiguriert/gefunden -- Abbruch (fail-open, kein Crash).")
        return 1

    try:
        queues = adapter.queues()
    except AdapterError as exc:
        print(f"Adapterfehler ({exc.kind}): {exc}", file=sys.stderr)
        return 2

    render_queues(queues)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
