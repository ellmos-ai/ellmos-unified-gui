# SPDX-License-Identifier: MIT
"""Test-Isolation: niemals Maschinen-/Shared-Configs laden und keine
Auto-Discovery der Standard-Layout-Pfade — Tests muessen auf jedem System
identisch laufen (UNIFIED_GUI_CONFIG ersetzt die Kaskade exklusiv)."""
import os

os.environ["UNIFIED_GUI_CONFIG"] = os.path.join(os.path.dirname(__file__), "_no_such_config.json")
os.environ["UNIFIED_GUI_DISCOVERY"] = "0"
# resolve_module_path() (config.py) is catalog-first for module_id-based
# backends (lock-master, ticket-master, clutch, decision-clicker); since
# T-20260902-901571937 ELLMOS_MODULES_CATALOG is exclusive like
# UNIFIED_GUI_CONFIG above. Without pointing it at a nonexistent file here,
# every create_app() test would fall through to the REAL host module
# catalog -- on a host with a real local decision-clicker clone, several
# degradation tests silently started resolving it for real (P10 appeared
# where the test expected it absent) purely because that host happens to
# have that clone. Tests must not depend on what is or isn't cloned locally.
os.environ["ELLMOS_MODULES_CATALOG"] = os.path.join(os.path.dirname(__file__), "_no_such_catalog.json")
# Audit-Log (audit_log.py) defaultet auf ~/.ellmos/unified-gui/audit.jsonl --
# ohne dieses "off" wuerde jeder create_app()-Test in das echte Nutzerprofil
# schreiben (gefunden 2026-08-18: ein erster Testlauf tat genau das, 10
# Zeilen in der realen Datei). Tests, die das Audit-Log selbst pruefen,
# ueberschreiben audit_log_path explizit in ihrem eigenen create_app(config=...).
os.environ["UNIFIED_GUI_AUDIT_LOG"] = "off"
