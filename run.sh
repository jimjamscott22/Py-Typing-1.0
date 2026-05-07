#!/bin/bash
# Shell script to launch Py-Typing-1.0

# Ensure we are in the directory containing the script
cd "$(dirname "$0")"

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed. Please install it first."
    echo "Visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

echo "Launching Py-Typing-1.0..."
uv run main.py
