# SPDX-License-Identifier: MIT
"""Test-Isolation: niemals die Maschinen-Config (unified-gui.config.json im cwd
oder ~/.unified_gui) laden — Tests muessen ueberall gleich laufen."""
import os

os.environ["UNIFIED_GUI_CONFIG"] = os.path.join(os.path.dirname(__file__), "_no_such_config.json")
