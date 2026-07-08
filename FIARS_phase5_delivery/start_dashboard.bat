@echo off
cd /d "%~dp0"
echo Starting FIARS Analytics Dashboard...
echo.
streamlit run dashboard\streamlit_app.py
if errorlevel 1 (
  echo.
  echo Dashboard failed to start.
  echo Make sure the dashboard extra is installed: pip install -r requirements-dashboard.txt
  echo.
  pause
)
