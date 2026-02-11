#!/bin/bash
# ================================================================
# SpatialSeed -- init.sh
# ================================================================
# Run once after cloning to set up the virtual environment,
# install Python dependencies, and initialise git submodules.
#
# Usage:
#   chmod +x init.sh
#   ./init.sh            # full setup
#   ./init.sh --no-models   # skip Essentia model download
# ================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="${PYTHON:-python3}"
SKIP_MODELS=false

for arg in "$@"; do
  case "$arg" in
    --no-models) SKIP_MODELS=true ;;
  esac
done

echo "================================"
echo "SpatialSeed init"
echo "================================"

# ------------------------------------------------------------------
# 1. Create virtual environment (if it does not already exist)
# ------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "[1/4] Creating virtual environment in .venv ..."
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "[1/4] Virtual environment already exists -- skipping creation."
fi

# ------------------------------------------------------------------
# 2. Install / upgrade Python dependencies
# ------------------------------------------------------------------
echo "[2/4] Installing Python dependencies ..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet

echo "  Core packages installed."

# ------------------------------------------------------------------
# 3. Initialise git submodules (non-recursive to avoid LFS issues)
# ------------------------------------------------------------------
echo "[3/4] Initialising git submodules ..."
git -C "$SCRIPT_DIR" submodule update --init

# ------------------------------------------------------------------
# 4. Optionally download Essentia ML models
# ------------------------------------------------------------------
if [ "$SKIP_MODELS" = false ]; then
  echo "[4/4] Essentia models"
  echo "  Do you want to download Essentia ML models? (y/n)"
  read -r answer
  if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    if [ ! -d "$SCRIPT_DIR/essentia/test/models" ]; then
      echo "  Downloading essentia models ..."
      mkdir -p "$SCRIPT_DIR/essentia/test/models"
      curl -L https://github.com/MTG/essentia-models/archive/refs/heads/master.zip \
        -o /tmp/models.zip
      unzip -q /tmp/models.zip -d /tmp
      mv /tmp/essentia-models-master/* "$SCRIPT_DIR/essentia/test/models/"
      rm -rf /tmp/essentia-models-master /tmp/models.zip
      echo "  Models downloaded."
    else
      echo "  Essentia models directory already exists -- skipping."
    fi
  else
    echo "  Skipping model download."
  fi
else
  echo "[4/4] Skipping Essentia model download (--no-models)."
fi

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
echo ""
echo "================================"
echo "Setup complete."
echo ""
echo "Activate the environment:"
echo "  source activate.sh"
echo ""
echo "Or manually:"
echo "  source .venv/bin/activate"
echo "================================"
