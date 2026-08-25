# SPDX-License-Identifier: MIT
"""Standalone-Start: python -m unified_gui [--port 8990] [--host 127.0.0.1]"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="unified-gui",
        description="ellmos Unified GUI -- Wheelhouse, the (desktop) app of the ControlRoom product: the console entrypoint into the shared control room. See README.md#wheelhouse.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8990)
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        raise SystemExit("uvicorn fehlt: pip install ellmos-unified-gui[serve]")

    from . import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
