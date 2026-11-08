@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher not found. Install Python 3.12 from python.org first.
  pause
  exit /b 1
)
py -3 -m pip install -r requirements.txt
if errorlevel 1 (echo Package installation failed & pause & exit /b 1)
py -3 Desktop\app.py
pause
