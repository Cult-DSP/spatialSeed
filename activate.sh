#!/bin/bash
# ================================================================
# SpatialSeed -- activate.sh
# ================================================================
# Source this script to activate the project virtual environment
# and set PYTHONPATH so that `src.*` imports resolve correctly.
#
# Usage:
#   source activate.sh
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Error: Virtual environment not found at $VENV_DIR"
  echo "Run ./init.sh first to create it."
  return 1 2>/dev/null || exit 1
fi

source "$VENV_DIR/bin/activate"

# Add the repo root to PYTHONPATH so `from src.* import ...` works
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "SpatialSeed environment activated."
echo "  Python : $(python --version 2>&1)"
echo "  venv   : $VENV_DIR"
echo "  PYTHONPATH includes: $SCRIPT_DIR"
