# SPDX-License-Identifier: MIT
"""Test-Isolation: niemals Maschinen-/Shared-Configs laden und keine
Auto-Discovery der Standard-Layout-Pfade — Tests muessen auf jedem System
identisch laufen (UNIFIED_GUI_CONFIG ersetzt die Kaskade exklusiv)."""
import os

os.environ["UNIFIED_GUI_CONFIG"] = os.path.join(os.path.dirname(__file__), "_no_such_config.json")
os.environ["UNIFIED_GUI_DISCOVERY"] = "0"
# Audit-Log (audit_log.py) defaultet auf ~/.ellmos/unified-gui/audit.jsonl --
# ohne dieses "off" wuerde jeder create_app()-Test in das echte Nutzerprofil
# schreiben (gefunden 2026-08-18: ein erster Testlauf tat genau das, 10
# Zeilen in der realen Datei). Tests, die das Audit-Log selbst pruefen,
# ueberschreiben audit_log_path explizit in ihrem eigenen create_app(config=...).
os.environ["UNIFIED_GUI_AUDIT_LOG"] = "off"
