# SpatialSeed

Offline authoring tool for immersive spatial audio scenes. Generates **LUSID scenes** and **ADM/BW64** exports from stereo mixes and isolated stems.

## Overview

SpatialSeed is a **LUSID-first** spatial audio authoring pipeline that:

- Takes a stereo reference mix + isolated stems
- Analyzes audio with MIR (Music Information Retrieval)
- Classifies instruments and assigns spatial roles
- Generates spatial placements and motion via the **Seed Matrix** interface
- Outputs **LUSID packages** for immediate rendering in sonoPleth
- Optionally exports **ADM/BW64** for DAW import (Logic Pro Atmos)

## Quick Start

### Installation

```bash
# Clone repository with submodules
git clone --recursive https://github.com/Cult-DSP/spatialSeed.git
cd spatialSeed

# Initialize submodules (essentia, LUSID)
./init.sh

# Install Python dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run pipeline from command line
python src/pipeline.py /path/to/stems --project-dir ./my_project -u 0.5 -v 0.3

# Or use the Streamlit UI
streamlit run ui/app.py
```

## Architecture

SpatialSeed follows a 9-stage pipeline:

1. **Session + Discovery** - Discover and validate stems
2. **Normalize Audio** - Resample to 48 kHz, split stereo to mono
3. **MIR Extraction** - Extract features using Essentia
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

**Drop-in compatible** with sonoPleth renderer.

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
├── internalDocsMD/           # Design specifications
│   ├── DesignSpecV1.md
│   ├── lowLevelSpecsV1.md
│   ├── agents.md
│   └── classify_README.md
├── LUSID/                    # LUSID submodule
├── essentia/                 # Essentia submodule (for models)
└── init.sh                   # Initialization script
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

**Version 0.1.0** - Initial implementation with pseudocode scaffolding

Current status:

- ✅ Complete module structure
- ✅ Comprehensive pseudocode and comments
- ⚠️ Implementation TODOs throughout
- ⚠️ Requires Essentia integration
- ⚠️ Requires LUSID transcoder integration
- ⚠️ Requires audio I/O library integration

## Documentation

- `internalDocsMD/DesignSpecV1.md` - High-level design specification
- `internalDocsMD/lowLevelSpecsV1.md` - Low-level architecture
- `internalDocsMD/agents.md` - Agent instructions and contracts
- `internalDocsMD/classify_README.md` - Classification module spec

## Dependencies

Core:

- Python 3.8+
- NumPy
- Essentia (for MIR + classification)
- LUSID (submodule, for ADM transcoding)

Audio I/O:

- librosa or soundfile (for WAV handling)
- scipy (for resampling)

UI (optional):

- Streamlit

See `requirements.txt` for complete list.

## License

TODO: Add license

## Contributing

See `internalDocsMD/agents.md` for development guidelines and non-negotiable contracts.

## Contact

Repository: https://github.com/Cult-DSP/spatialSeed
