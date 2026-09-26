@echo off
setlocal
cd /d "%~dp0"
title Algobot Trading Desk

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% --version >nul 2>nul
if errorlevel 1 goto nopython

if not exist ".venv\Scripts\python.exe" (
  echo First run: setting things up. This takes a few minutes, once.
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Could not create the working folder. Make sure Python 3.10 or newer is installed.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Install failed. Check your internet connection and run this again.
  pause
  exit /b 1
)
echo.
echo Starting the trading desk. Your browser will open. Close this window to stop it.
streamlit run dashboard.py
pause
exit /b 0

:nopython
echo.
echo Python is not installed on this computer.
echo   1. Go to https://www.python.org/downloads/ and install Python 3.10 or newer.
echo   2. During the install, TICK the box "Add python.exe to PATH".
echo   3. Then double-click this file again.
echo.
pause
exit /b 1
