@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"

if not defined LOCALAPPDATA (
  echo ERROR: LOCALAPPDATA is not available.
  exit /b 1
)

set "SABT_DATA_DIR=%LOCALAPPDATA%\SABT\data"
set "SABT_LOG_DIR=%LOCALAPPDATA%\SABT\logs"
set "SABT_RUN_DIR=%LOCALAPPDATA%\SABT\run"
set "PID_FILE=%SABT_RUN_DIR%\server.pid"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo SABT is not installed. Run setup.bat first.
  exit /b 1
)
if not exist "%SABT_DATA_DIR%" mkdir "%SABT_DATA_DIR%"
if not exist "%SABT_LOG_DIR%" mkdir "%SABT_LOG_DIR%"
if not exist "%SABT_RUN_DIR%" mkdir "%SABT_RUN_DIR%"

echo Checking database migrations...
"%PYTHON_EXE%" -m alembic upgrade head
if errorlevel 1 (
  echo ERROR: Database migration failed. SABT was not started.
  exit /b 1
)

for /f "delims=" %%S in ('"%PYTHON_EXE%" -m app.bootstrap --status') do set "BOOTSTRAP_STATUS=%%S"
if errorlevel 1 (
  echo ERROR: Could not inspect administrator status.
  exit /b 1
)
if /I "%BOOTSTRAP_STATUS%"=="needs-admin" (
  if "%SABT_SKIP_BOOTSTRAP%"=="1" (
    echo Administrator creation skipped by SABT_SKIP_BOOTSTRAP.
  ) else (
    "%PYTHON_EXE%" -m app.bootstrap
    if errorlevel 1 exit /b 1
  )
)

for /f "delims=" %%P in ('powershell -NoProfile -Command "if (Test-Path '%PID_FILE%') { $serverProcessId = (Get-Content '%PID_FILE%' -Raw).Trim(); $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $serverProcessId) -ErrorAction SilentlyContinue; if ($p -and $p.CommandLine -match 'uvicorn app.main:app') { Write-Output 'RUNNING' } else { Remove-Item '%PID_FILE%' -Force -ErrorAction SilentlyContinue } }"') do set "SERVER_STATE=%%P"
if /I "%SERVER_STATE%"=="RUNNING" (
  echo SABT is already running at http://127.0.0.1:8000/portal/
  if not "%SABT_NO_BROWSER%"=="1" start "" "http://127.0.0.1:8000/portal/"
  exit /b 0
)

echo Starting SABT local server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory '%ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%SABT_LOG_DIR%\server.log' -RedirectStandardError '%SABT_LOG_DIR%\server-error.log' -PassThru; Set-Content -Path '%PID_FILE%' -Value $p.Id"
if errorlevel 1 (
  echo ERROR: Could not launch SABT. Check %SABT_LOG_DIR%\server-error.log
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ready = $false; for ($i = 0; $i -lt 20; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { $ready = $true; break } } catch { }; Start-Sleep -Milliseconds 500 }; if ($ready) { if ($env:SABT_NO_BROWSER -ne '1') { Start-Process 'http://127.0.0.1:8000/portal/' }; exit 0 }; exit 1"
if errorlevel 1 (
  echo ERROR: SABT did not become healthy. Check %SABT_LOG_DIR%\server-error.log
  call "%ROOT%stop.bat"
  exit /b 1
)

echo SABT is ready at http://127.0.0.1:8000/portal/
echo Logs: %SABT_LOG_DIR%
exit /b 0
