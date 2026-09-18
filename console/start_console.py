# SPDX-License-Identifier: MIT
"""Repo-Einstieg für das importierbare Konsolenstartfenster."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unified_gui.console.start_console import main  # noqa: E402

raise SystemExit(main())
