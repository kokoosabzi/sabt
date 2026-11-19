@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"

if not defined LOCALAPPDATA (
  echo ERROR: LOCALAPPDATA is not available. Run this script from a Windows user session.
  exit /b 1
)

set "SABT_DATA_DIR=%LOCALAPPDATA%\SABT\data"
set "SABT_LOG_DIR=%LOCALAPPDATA%\SABT\logs"
set "SABT_RUN_DIR=%LOCALAPPDATA%\SABT\run"
if not exist "%SABT_DATA_DIR%" mkdir "%SABT_DATA_DIR%"
if not exist "%SABT_LOG_DIR%" mkdir "%SABT_LOG_DIR%"
if not exist "%SABT_RUN_DIR%" mkdir "%SABT_RUN_DIR%"

where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python Launcher was not found. Install Python 3.12 and enable the Python Launcher.
  exit /b 1
)
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.12 was not found. Install Python 3.12 before continuing.
  exit /b 1
)

if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo Creating SABT virtual environment...
  py -3.12 -m venv "%ROOT%.venv"
  if errorlevel 1 (
    echo ERROR: Could not create the Python virtual environment.
    exit /b 1
  )
)

set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"
echo Installing SABT and its dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  exit /b 1
)
"%PYTHON_EXE%" -m pip install -e .
if errorlevel 1 (
  echo ERROR: SABT dependency installation failed.
  exit /b 1
)

echo Applying database migrations...
"%PYTHON_EXE%" -m alembic upgrade head
if errorlevel 1 (
  echo ERROR: Database migration failed. Existing data has not been intentionally moved or deleted.
  exit /b 1
)

for /f "delims=" %%S in ('"%PYTHON_EXE%" -m app.bootstrap --status') do set "BOOTSTRAP_STATUS=%%S"
if errorlevel 1 (
  echo ERROR: Could not inspect initial administrator status.
  exit /b 1
)

if /I "%BOOTSTRAP_STATUS%"=="needs-admin" (
  if "%SABT_SKIP_BOOTSTRAP%"=="1" (
    echo Administrator creation skipped by SABT_SKIP_BOOTSTRAP.
  ) else (
    echo Create the first SABT administrator:
    "%PYTHON_EXE%" -m app.bootstrap
    if errorlevel 1 (
      echo ERROR: Initial administrator setup failed.
      exit /b 1
    )
  )
) else if /I "%BOOTSTRAP_STATUS%"=="configured" (
  echo Existing user accounts detected. No account was changed.
) else (
  echo ERROR: Unexpected bootstrap status "%BOOTSTRAP_STATUS%".
  exit /b 1
)

echo.
echo SABT setup completed.
echo Data directory: %SABT_DATA_DIR%
echo Run start.bat to launch the local application.
exit /b 0
