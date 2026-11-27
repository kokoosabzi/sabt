@echo off
setlocal EnableExtensions
if not defined LOCALAPPDATA (
  echo ERROR: LOCALAPPDATA is not available.
  exit /b 1
)
set "SABT_RUN_DIR=%LOCALAPPDATA%\SABT\run"
set "PID_FILE=%SABT_RUN_DIR%\server.pid"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-server.ps1" -PidFile "%PID_FILE%"
if errorlevel 1 (
  echo ERROR: Could not stop the SABT process.
  exit /b 1
)
exit /b 0
