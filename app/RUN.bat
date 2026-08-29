@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating the Floppyverse environment...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 goto :failed
)

echo Checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

".venv\Scripts\python.exe" -m floppyverse
if errorlevel 1 pause
exit /b 0

:failed
echo.
echo Setup failed. Install Python 3.10 or newer from https://python.org,
echo select "Add Python to PATH", then run this file again.
pause
exit /b 1

