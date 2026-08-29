@echo off
setlocal
cd /d "%~dp0"

>"floppyverse-launch.log" echo Floppyverse startup log

if not exist ".venv\Scripts\pythonw.exe" (
  >>"floppyverse-launch.log" echo Creating the Python environment...
  py -3 -m venv .venv 2>>"floppyverse-launch.log" || python -m venv .venv 2>>"floppyverse-launch.log"
  if errorlevel 1 exit /b 1

  >>"floppyverse-launch.log" echo Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt >>"floppyverse-launch.log" 2>&1
  if errorlevel 1 exit /b 1
)

>>"floppyverse-launch.log" echo Starting the interface...
".venv\Scripts\pythonw.exe" -m floppyverse >>"floppyverse-launch.log" 2>&1
exit /b %errorlevel%

