#!/bin/bash
set -e

# R.A.P.H.A.E.L launcher
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Checking requirements..."

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON not found. Install Python 3 first."
    exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
    echo "WARNING: 'ollama' not found on PATH. The app may not respond."
fi

if ! command -v piper >/dev/null 2>&1; then
    echo "WARNING: 'piper' not found on PATH. Voice output will not work."
fi

if [ ! -f "Non_Github_Dependencies/Voices/en_GB-alan-medium.onnx" ]; then
    echo "WARNING: Voice model file not found. Voice output may fail."
fi

echo "Starting R.A.P.H.A.E.L..."
exec "$PYTHON" Main.py