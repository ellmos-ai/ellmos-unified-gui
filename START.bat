@echo off
rem START.bat — ellmos Unified GUI ohne Installation starten (Default-Port 8990).
rem Laeuft aus jedem Checkout und jeder Plan-D-Deploykopie (auch OneDrive):
rem src/ wird ueber %~dp0 auf den PYTHONPATH gelegt, es ist kein pip install
rem noetig. Voraussetzungen: Python 3.10+ mit fastapi, jinja2, uvicorn.
rem Aufruf: START.bat [--port 8990] [--host 127.0.0.1]
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0src;%PYTHONPATH%
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m unified_gui %*
) else (
  python -m unified_gui %*
)
endlocal
