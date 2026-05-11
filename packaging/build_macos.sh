#!/bin/bash
set -e

# SpatialSeed macOS Build Script
# -----------------------------
# This script builds the SpatialSeed prototype app using PyInstaller.

echo "--- SpatialSeed Build (macOS) ---"

# 1. Ensure we are in the packaging directory
cd "$(dirname "$0")"

# 2. Check if venv is active or available
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "../.venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source ../.venv/bin/activate
    else
        echo "Error: Virtual environment not found. Please run ./init.sh in the repo root first."
        exit 1
    fi
fi

# 3. Ensure PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found in venv. Installing..."
    pip install pyinstaller
fi

# 4. Ensure CULT Transcoder binary exists
CULT_BIN="../cult_transcoder/build/cult-transcoder"
if [ ! -f "$CULT_BIN" ]; then
    echo "Error: CULT Transcoder binary not found at $CULT_BIN"
    echo "Please build it first: cd cult_transcoder && cmake -B build && cmake --build build"
    exit 1
fi

# 5. Clean previous build artifacts
echo "Cleaning old artifacts..."
rm -rf build dist

# 6. Run PyInstaller
echo "Running PyInstaller..."
pyinstaller --noconfirm spatialseed.spec

echo "--- Build Complete ---"
echo "Packaged app can be found in: packaging/dist/SpatialSeed"
echo "To run: ./dist/SpatialSeed/SpatialSeed"
