#!/bin/bash

# Script to initialize and update git submodules

echo "Initializing and updating git submodules..."

# Update main submodules (non-recursive to avoid LFS issues)
git submodule update --init

# Download essentia models manually to avoid LFS
if [ ! -d "essentia/test/models" ]; then
    echo "Downloading essentia models..."
    mkdir -p essentia/test/models
    curl -L https://github.com/MTG/essentia-models/archive/refs/heads/master.zip -o /tmp/models.zip
    unzip /tmp/models.zip -d /tmp
    mv /tmp/essentia-models-master/* essentia/test/models/
    rm -rf /tmp/essentia-models-master /tmp/models.zip
fi

if [ $? -eq 0 ]; then
    echo "Git submodules and models updated successfully."
else
    echo "Failed to update git submodules or models."
    exit 1
fi
