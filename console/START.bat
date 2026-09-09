@echo off
setlocal
set "REPO=%~dp0.."
set "PYTHONPATH=%REPO%\src;%PYTHONPATH%"
python -m unified_gui.console start %*
exit /b %ERRORLEVEL%
