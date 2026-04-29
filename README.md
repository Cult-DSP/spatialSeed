# SpatialSeed

Offline authoring tool for immersive spatial audio scenes. Generates **LUSID scenes** and **ADM/BW64** exports from stereo mixes and isolated stems.

## Overview

SpatialSeed is a **LUSID-first** spatial audio authoring pipeline that:

- Takes a stereo reference mix + isolated stems
- Analyzes audio with MIR (Music Information Retrieval)
- Classifies instruments and assigns spatial roles
- Generates spatial placements and motion via the **Seed Matrix** interface
- Outputs **LUSID packages** for immediate rendering in Spatial Root
- Optionally exports **ADM/BW64** for DAW import (Logic Pro Atmos)

## Quick Start

### Installation

```bash
# Clone repository with submodules
git clone --recursive https://github.com/Cult-DSP/spatialSeed.git
cd spatialSeed

# Run init.sh -- creates .venv, installs deps, inits submodules
chmod +x init.sh activate.sh
./init.sh

# Activate the virtual environment (sets PYTHONPATH too)
source activate.sh
```

### Basic Usage

#### Command Line

```bash
# Activate the virtual environment
source activate.sh

# Run pipeline with default parameters (u=0.5, v=0.3)
python -m src.pipeline /path/to/stems --project-dir ./my_project

# Run with custom Seed Matrix parameters
python -m src.pipeline /path/to/stems --project-dir ./my_project -u 0.5 -v 0.3

# Export ADM/BW64 in addition to LUSID package
python -m src.pipeline /path/to/stems --project-dir ./my_project --export-adm

# Example (macOS):
python -m src.pipeline ~/Desktop/stems --project-dir ~/spatialSeed_output -u 0.5 -v 0.3
```

#### Streamlit UI

```bash
# Activate the virtual environment
source activate.sh

# Launch interactive web UI (opens at http://localhost:8501)
streamlit run ui/app.py
```

The UI provides:
- Interactive 2D Seed Matrix control (u, v sliders)
- Stem discovery and classification review
- Per-stem category/role overrides
- Real-time progress tracking
- Results visualization and export management

## Architecture

SpatialSeed follows a 9-stage pipeline:

1. **Session + Discovery** - Discover and validate stems
2. **Normalize Audio** - Resample to 48 kHz, split stereo to mono
3. **MIR Extraction** - Extract features using librosa
4. **Classification** - Classify instruments (category + role)
5. **Seed Matrix** - Map (u,v) selection to style vector z
6. **SPF Resolution** - Resolve spatial style profiles
7. **Placement** - Compute static XYZ positions
8. **Gesture Generation** - Create sparse motion keyframes
9. **Export** - LUSID package + optional ADM/BW64

## Seed Matrix

The **Seed Matrix** is a 2D control surface for spatial authoring:

- **u axis** (0-1): Aesthetic variation (conservative → experimental)
- **v axis** (0-1): Dynamic immersion (static → enveloping/animated)

Selection point (u,v) maps to a style vector z that governs:

- Placement spread
- Height usage
- Motion intensity and complexity
- Symmetry and spatial distribution
- MIR coupling (feature → motion modulation)

## Outputs

### LUSID Package (Primary)

A folder containing:

- `scene.lusid.json` - LUSID Scene v0.5.x
- `containsAudio.json` - Channel metadata
- `mir_summary.json` - MIR feature summaries
- Mono WAVs: `1.1.wav`, `2.1.wav`, ..., `LFE.wav`, `11.1.wav`, ...

**Drop-in compatible** with Spatial Root renderer.

### ADM/BW64 Export (Optional)

- `export.adm.wav` - BW64 with embedded ADM XML
- `export.adm.xml` - Sidecar XML (debug)

**Import into Logic Pro Atmos** for DAW editing.

## Project Structure

```
spatialSeed/
├── src/
│   ├── pipeline.py           # Main orchestrator
│   ├── session.py            # Session management
│   ├── audio_io.py           # Audio normalization
│   ├── mir/
│   │   ├── extract.py        # MIR feature extraction
│   │   └── classify.py       # Instrument classification
│   ├── seed_matrix.py        # Seed Matrix mapping
│   ├── spf.py                # Spatial Prior Field
│   ├── placement.py          # Static placement
│   ├── gesture_engine.py     # Motion generation
│   ├── lusid_writer.py       # LUSID scene assembly
│   └── export/
│       ├── lusid_package.py  # LUSID package exporter
│       └── adm_bw64.py       # ADM/BW64 exporter
├── ui/
│   └── app.py                # Streamlit UI
├── config/
│   └── defaults.json         # Default configuration
├── templates/
│   └── directSpeakerData.json # Bed/direct-speaker template
├── internalDocs/           # Design specifications
│   ├── DesignSpecV1.md
│   ├── lowLevelSpecsV1.md
│   ├── agents.md
│   └── classify_README.md
├── LUSID/                    # LUSID submodule
├── essentia/                 # Essentia submodule (for models)
├── init.sh                   # One-time setup (venv + deps + submodules)
└── activate.sh               # Activate venv for each session
```

## Configuration

See `config/defaults.json` for default settings. Key parameters:

- `sample_rate`: 48000 (fixed in v1)
- `audio_format`: float32 (fixed in v1)
- `seed_matrix.default_u`: Default aesthetic variation
- `seed_matrix.default_v`: Default dynamic immersion
- `mir.category_threshold`: Classification confidence threshold
- `gesture.position_epsilon`: Keyframe emission threshold

## Development Status

**Version 0.2.0** - Core pipeline operational with MIR-driven enhancements

**Pipeline stages** (all stages 0-9A complete):
- [DONE] Session + Discovery (stage 0)
- [DONE] Normalize Audio (stage 1)
- [DONE] MIR Extraction (stage 2)
- [DONE] Classification (stage 3)
- [DONE] Seed Matrix (stage 4)
- [DONE] SPF Resolution with Priority 1, 2, 5 enhancements (stage 5)
- [DONE] Static Placement (stage 6)
- [DONE] Gesture Generation (stage 7)
- [DONE] LUSID Scene Assembly (stage 8)
- [DONE] LUSID Package Export (stage 9)
- [DONE] Optional ADM/BW64 Export (stage 9A)

**Recent enhancements** (Phase 8, April 2026):
- [DONE] **Priority 1**: Context-aware profile selection (genre/energy/density modulation)
- [DONE] **Priority 2**: Frequency-elevation coupling (spectral_centroid-based constraints)
- [DONE] **Priority 5**: MIR tier 2 modulation (energy/flux/brightness → spread/motion_intensity)
- [DEFERRED] **Priority 3**: Gesture parametric motion v3.1+ (tempo sync, onset reactivity)
- [DEFERRED] **Priority 4**: Per-stem UI tuning v3.2+ (visual feedback refinements)
- [TODO] **Priority 6**: Multi-stem validation framework

**UI and tooling:**
- [DONE] Streamlit UI with Seed Matrix 2D control
- [DONE] Command-line interface with full pipeline
- [DONE] LUSID package generation (drop-in for Spatial Root)
- [DONE] ADM/BW64 export (Logic Pro Atmos compatible)

## Documentation

- `internalDocs/DesignSpecV1.md` - High-level design specification
- `internalDocs/lowLevelSpecsV1.md` - Low-level architecture
- `internalDocs/agents.md` - Agent instructions and contracts
- `internalDocs/classify_README.md` - Classification module spec

## Dependencies

Core:

- Python 3.10+
- NumPy, SciPy
- librosa (audio resampling + MIR feature extraction)
- soundfile (audio I/O)
- LUSID (submodule, for ADM transcoding)

UI (optional):

- Streamlit

See `requirements.txt` for complete list.

## License

TODO: Add license

## Contributing

See `internalDocs/agents.md` for development guidelines and non-negotiable contracts.

## Contact

Repository: https://github.com/Cult-DSP/spatialSeed
