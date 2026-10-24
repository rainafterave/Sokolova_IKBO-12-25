#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec "${PYTHON_EXE:-python3}" src/main.py "$@"
