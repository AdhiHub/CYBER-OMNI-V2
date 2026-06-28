#!/bin/bash
# AdhiHub CYBER-OMNI - Quick start
# Handles venv activation automatically

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python omni.py "$@"
