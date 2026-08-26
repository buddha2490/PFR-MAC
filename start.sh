#!/bin/bash
# PFR Sentinel — macOS launcher
#
# Mirrors start.bat. Runs the app from the project's own virtualenv so it does
# not matter what Python (if any) is on PATH.
#
#   ./start.sh                 # normal GUI
#   ./start.sh --auto-start    # GUI, begin capturing immediately
#   ./start.sh --headless      # no GUI, web server only

set -e
cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
    echo "Virtualenv missing at $VENV"
    echo "Create it with:  uv venv --python 3.12 $VENV && uv pip install -r requirements.txt"
    exit 1
fi

# The ZWO SDK is vendored under sdk/macos/ and relinked to a sibling libusb,
# so no Homebrew or system install is required. Warn rather than fail: the
# directory-watch capture mode works fine without a camera.
SDK="sdk/macos/libASICamera2.dylib"
if [ ! -f "$SDK" ]; then
    echo "Warning: ASI SDK not found at $SDK — ZWO camera capture will be unavailable."
fi

exec "$PY" main.py "$@"
