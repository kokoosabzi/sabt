@echo off
setlocal EnableExtensions
if not defined LOCALAPPDATA (
  echo ERROR: LOCALAPPDATA is not available.
  exit /b 1
)
set "SABT_RUN_DIR=%LOCALAPPDATA%\SABT\run"
set "PID_FILE=%SABT_RUN_DIR%\server.pid"

if not exist "%PID_FILE%" (
  echo SABT is not running (no PID file).
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$path = '%PID_FILE%'; $raw = Get-Content $path -Raw -ErrorAction SilentlyContinue; $serverProcessId = 0; if ([int]::TryParse(($raw -as [string]).Trim(), [ref]$serverProcessId)) { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $serverProcessId) -ErrorAction SilentlyContinue; if ($p -and $p.CommandLine -match 'uvicorn app.main:app') { Stop-Process -Id $serverProcessId -Force -ErrorAction Stop; Start-Sleep -Milliseconds 500 } }; Remove-Item $path -Force -ErrorAction SilentlyContinue"
if errorlevel 1 (
  echo ERROR: Could not stop the SABT process.
  exit /b 1
)
echo SABT stopped.
exit /b 0
