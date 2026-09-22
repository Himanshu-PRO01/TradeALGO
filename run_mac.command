#!/bin/bash
# Double-click this file in Finder (Mac). On Linux run:  bash run_mac.command
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "Python 3 is not installed."
  echo "Install it from https://www.python.org/downloads/ and then run this file again."
  read -r -p "Press Enter to close" _
  exit 1
fi

if [ ! -d .venv ]; then
  echo "First run: setting things up. This takes a few minutes, once."
  python3 -m venv .venv || { echo "Could not create the working folder."; read -r -p "Press Enter to close" _; exit 1; }
fi
source .venv/bin/activate
python -m pip install --quiet --disable-pip-version-check -r requirements.txt || { echo "Install failed. Check your internet connection."; read -r -p "Press Enter to close" _; exit 1; }
echo
echo "Starting the trading desk. Your browser will open. Close this window to stop it."
streamlit run Trading_Desk.py
