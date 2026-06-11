#!/bin/bash
# Shell script to launch Py-Typing-1.0

# Ensure we are in the directory containing the script
cd "$(dirname "$0")"

# Desktop launchers have a minimal PATH; resolve uv explicitly
UV_BIN="${HOME}/.local/bin/uv"
if [ ! -x "$UV_BIN" ]; then
    UV_BIN="$(command -v uv 2>/dev/null)"
fi

if [ -z "$UV_BIN" ]; then
    zenity --error --text="uv is not installed. Visit https://docs.astral.sh/uv/getting-started/installation/" 2>/dev/null \
        || echo "Error: uv is not installed." >&2
    exit 1
fi

"$UV_BIN" run main.py
