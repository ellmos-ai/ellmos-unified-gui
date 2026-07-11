# SPDX-License-Identifier: MIT
"""Test-Isolation: niemals Maschinen-/Shared-Configs laden und keine
Auto-Discovery der Standard-Layout-Pfade — Tests muessen auf jedem System
identisch laufen (UNIFIED_GUI_CONFIG ersetzt die Kaskade exklusiv)."""
import os

os.environ["UNIFIED_GUI_CONFIG"] = os.path.join(os.path.dirname(__file__), "_no_such_config.json")
os.environ["UNIFIED_GUI_DISCOVERY"] = "0"
