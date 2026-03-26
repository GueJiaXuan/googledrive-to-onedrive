#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

find_python() {
  if command -v python3.12 >/dev/null 2>&1; then
    command -v python3.12
    return
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return
  fi
  if command -v python3.10 >/dev/null 2>&1; then
    command -v python3.10
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    if [ $? -eq 0 ]; then
      command -v python3
      return
    fi
  fi

  echo "No supported Python found (need 3.10+)." >&2
  echo "On macOS, install one with: brew install python@3.12" >&2
  exit 1
}

PYTHON_BIN="$(find_python)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Using Python: $PYTHON_BIN"
echo "Creating/updating virtual environment in $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

VENV_PYTHON="$VENV_DIR/bin/python"

"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
"$VENV_PYTHON" -m pip install \
  pandas geopandas fiona \
  google-api-python-client google-auth google-auth-oauthlib openpyxl

echo "Setup complete."
echo "Run the app with: ./run.sh"
