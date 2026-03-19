#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/PROJECT_CPSA_2026/PROJECT_CPSA_FILES" || exit 1
exec python3.10 main.py
