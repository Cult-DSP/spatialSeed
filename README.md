# SpatialSeed

Offline authoring tool for immersive spatial audio scenes. Generates **LUSID scenes** and **ADM/BW64** exports from stereo mixes and isolated stems.

## Overview

SpatialSeed is a **LUSID-first** spatial audio authoring pipeline that:

- Takes a stereo reference mix + isolated stems
- Analyzes audio with MIR (Music Information Retrieval)
- Classifies instruments and assigns spatial roles
- Generates spatial placements and motion via the **Seed Matrix** interface
- Outputs **LUSID packages** for immediate rendering in Spatial Root
- Optionally exports **ADM/BW64** for DAW import (Logic Pro Atmos) via CULT Transcoder

## Quick Start

### Installation

```bash
# Clone repository with submodules
git clone --recursive https://github.com/Cult-DSP/spatialSeed.git
cd spatialSeed

# Run init.sh -- creates .venv, installs deps, inits submodules
chmod +x init.sh activate.sh
./init.sh

# Build CULT Transcoder (required for ADM export)
cd cult_transcoder
cmake -B build
cmake --build build --parallel
cd ..

# Activate the virtual environment
source activate.sh
```

### Basic Usage (CLI)

```bash
# Activate the virtual environment
source activate.sh

# Run pipeline with default parameters
python -m src.pipeline /path/to/stems --project-dir ./my_project -u 0.5 -v 0.3

# Export ADM/BW64 in addition to LUSID package
python -m src.pipeline /path/to/stems --project-dir ./my_project -u 0.5 -v 0.3 --export-adm
```

### Basic Usage (GUI)

```bash
# Launch interactive web UI (opens at http://localhost:8501)
streamlit run ui/app.py
```

## Documentation

The documentation has been consolidated into the `docs/` directory:

- [Architecture](docs/ARCHITECTURE.md) - Pipeline stages and components.
- [Workflows](docs/WORKFLOW.md) - Using the CLI and GUI.
- [Exports](docs/EXPORTS.md) - Details on LUSID Package and ADM BWF generation.
- [Placement Engine](docs/PLACEMENT_ENGINE.md) - How Seed Matrix, SPF, Placement, and Gestures work.
- [User Interface](docs/UI.md) - Streamlit dashboard details.
- [Validation](docs/VALIDATION.md) - Testing and verification instructions.
- [AGENTS.md](AGENTS.md) - Guidelines and rules for AI contributors.

*Historical planning documents can be found in `internalDocs/archive/`.*

## License

TODO: Add license
