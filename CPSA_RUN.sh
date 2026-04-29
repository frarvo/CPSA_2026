#!/bin/bash
# Open a real GNOME terminal, run main.py, and close when it finishes
gnome-terminal --working-directory="$(dirname "$0")/PROJECT_CPSA_2026" -- bash -c "python3.10 main.py; exec bash"
