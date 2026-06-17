@echo off
cd /d "%~dp0"
echo Starting FIARS...
echo.
python server.py
if errorlevel 1 (
  echo.
  echo FIARS failed to start.
  echo Make sure Python 3.10+ is installed: python --version
  echo.
  pause
)
