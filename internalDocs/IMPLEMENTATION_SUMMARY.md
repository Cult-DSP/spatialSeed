# SpatialSeed - Implementation Summary

**Date:** 2026-02-11 (Updated)
**Status:** Stages 0-9A implemented and validated with real stems. Streamlit UI complete. ADM export deferred.

## Important for New Agents

**ENVIRONMENT SETUP (do this first):**

```bash
./init.sh          # one-time: creates .venv, installs deps, inits submodules
source activate.sh # each session: activates venv + sets PYTHONPATH
```

**THEN:**

1. Read this file (overview of what is built)
2. Read `agents.md` Section 14 -- implementation roadmap with phases
3. Follow the phase-by-phase plan in `agents.md`

**agents.md has been updated with:**

- Section 14: Detailed implementation roadmap (6 phases)
- Section 15: Resources and quick tips
- Code examples for common tasks
- Test milestones for each phase

## What Was Created

A complete repository structure for SpatialSeed with detailed pseudocode and comments based on the specifications in `internalDocs/`.

### Directory Structure

```
spatialSeed/
├── src/                          # Core pipeline modules
│   ├── __init__.py
│   ├── pipeline.py               # Main orchestrator (9 stages)
│   ├── session.py                # Stage 0: Discovery & manifest
│   ├── audio_io.py               # Stage 1: Audio normalization
│   ├── mir/
│   │   ├── __init__.py
│   │   ├── extract.py            # Stage 2: MIR feature extraction
│   │   └── classify.py           # Stage 3: Instrument classification
│   ├── seed_matrix.py            # Stage 4: (u,v) → style vector z
│   ├── spf.py                    # Stage 5: SPF & StyleProfile resolution
│   ├── placement.py              # Stage 6: Static XYZ placement
│   ├── gesture_engine.py         # Stage 7: Sparse keyframe generation
│   ├── lusid_writer.py           # Stage 8: LUSID scene assembly
│   └── export/
│       ├── __init__.py
│       ├── lusid_package.py      # Stage 9A: LUSID package export
├── ui/
│   └── app.py                    # Streamlit UI entry point
├── config/
│   └── defaults.json             # Default configuration
├── templates/
│   └── directSpeakerData.json    # Bed/direct-speaker template
├── cache/                        # (Created dynamically)
├── tests/                        # (Empty, ready for tests)
├── internalDocs/               # Design specifications (existing)
│   ├── DesignSpecV1.md
│   ├── lowLevelSpecsV1.md
│   ├── agents.md
│   └── classify_README.md
├── LUSID/                        # LUSID submodule (existing)
├── essentia/                     # Essentia submodule (existing)
├── init.sh                       # Initialization script (existing)
├── .gitignore
├── .gitmodules                   # Submodule config (existing)
├── README.md                     # Project overview
└── requirements.txt              # Python dependencies
```

## Module Summaries

### Core Pipeline (src/pipeline.py)

- Orchestrates all 9 stages
- Command-line interface
- Configuration loading
- Results saving

### Stage 0: Session (src/session.py)

- Stem discovery and validation
- Deterministic ID allocation (groups 11+)
- Stereo → two mono objects
- Manifest generation

### Stage 1: Audio I/O (src/audio_io.py)

- Resample to 48 kHz (no gain changes in v1)
- Stereo splitting to mono
- Silent bed/LFE WAV generation
- Float32 format

### Stage 2: MIR Extract (src/mir/extract.py)

- librosa-based feature extraction (not Essentia -- Essentia is optional for classification only)
- Uses `soundfile` for ultra-fast loading combined with a shared `librosa.stft` to significantly optimize redundant time-to-frequency conversions.
- Parallelized batch extraction leveraging `concurrent.futures.ProcessPoolExecutor` to crunch large stem counts instantly on multicore machines.
- Per-stem features: RMS energy, spectral centroid (mean+std), spectral flux, onset density,
  pitch confidence (piptrack), harmonic ratio (HPSS), spectral flatness, zero-crossing rate
- Stereo mix features (mid/side width, L/R energy balance, L/R correlation)
- Hash-based JSON caching
- mir_summary.json output
- MIR heuristic helper functions for category and role inference (used by classify.py)

### Stage 3: Classification (src/mir/classify.py)

- Lazy Essentia TF model import (works without essentia-tensorflow installed)
- Models (when available):
  - Instrument: mtg_jamendo_instrument-discogs-effnet
  - Role: fs_loop_ds-msd-musicnn
- Canonical categories: vocals, bass, drums, guitar, keys, strings, pads, fx, other, unknown
- Role hints: bass, rhythm, lead, percussion, fx, unknown
- Three-tier fallback chain: Essentia models -> filename regex -> MIR heuristics
- Filename patterns: vox/vocal/LV/BV, drum/perc/kick/snare/hat, bass, gtr/guitar/aco/acoustic,
  piano/keys/rhodes/organ, string, synth/pad, fx/sfx/noise/ambient
- MIR heuristics tuned against real 96 kHz stereo stems
- Classification caching

### Stage 4: Seed Matrix (src/seed_matrix.py)

- Maps (u,v) → style vector z (8-dimensional)
- u: aesthetic variation (0=conservative, 1=experimental)
- v: dynamic immersion (0=static, 1=animated)
- Style vector components:
  - Placement spread, height usage, motion intensity, complexity
  - Symmetry, front-back bias, ensemble cohesion, MIR coupling

### Stage 5: SPF (src/spf.py)

- Spatial Prior Field with InstrumentProfile definitions
- (InstrumentProfile, z, MIR, tags) → StyleProfile
- Base placement tendencies (azimuth, elevation, distance)
- Motion archetypes: static, drift, orbit, reactive
- MIR coupling sensitivities
- Minimal trace for reproducibility

### Stage 6: Placement (src/placement.py)

- Static XYZ positions in normalized cube [-1,1]³
- +X=right, +Y=front, +Z=up
- Style vector modulations
- Constraints (symmetry, front-back, height)
- Cube clamping with logging

### Stage 7: Gesture Engine (src/gesture_engine.py)

- Sparse keyframe generation
- Motion types: static, drift, orbit, reactive
- Keyframe emission thresholds (position, spread)
- MIR-reactive motion (future)
- Ensures t=0.0 keyframe for all sources

### Stage 8: LUSID Writer (src/lusid_writer.py)

- Assembles LUSID Scene v0.5.x
- Delta frames (changing nodes only)
- Bed/direct-speaker nodes at t=0
- LFE special case (node 4.1, file LFE.wav)
- scene.lusid.json output

### Stage 9A: LUSID Package (src/export/lusid_package.py)

- Package folder creation
- containsAudio.json generation (ADM channel order)
- mir_summary.json copy
- WAV file organization
- Package validation

### Stage 9B: ADM/BW64 (Delegated to cult_transcoder)

- Python implementation removed.
- Handled entirely by `cult_transcoder` C++ submodule (`src/authoring`).

### UI (ui/app.py)

- Streamlit interface (fully implemented)
- Seed Matrix sliders (u, v) in sidebar with 0.01 step
- Discover Stems button (runs Stage 0 only for fast feedback)
- Per-stem expander with metadata, classification results, and override controls
- Category/role override selectboxes per node (injected into pipeline via classification_overrides)
- Generate Scene button with stdout capture and progress display
- Results tab: keyframe metrics, style vector breakdown, classification table, export paths
- Pipeline log viewer in expandable section

## Implementation Status

### [DONE] Implemented

- Full module structure with `src.*` package imports
- Virtual environment setup (`init.sh` / `activate.sh`)
- Config-driven architecture routing `config/defaults.json` through all stages
- Validation of mono stem inputs edge cases
- Renamed all instances of "sonoPleth" to "Spatial Root"
- **Stage 0 -- session.py:** stem discovery, validation, deterministic ID allocation
- **Stage 1 -- audio_io.py:** librosa resampling, mono + stereo handling
- **Stage 2 -- mir/extract.py:** librosa-based feature extraction
- **Stage 3 -- mir/classify.py:** heuristics and ML categorization
- **Stage 4 -- seed_matrix.py:** analytic (u,v) to z mapping
- **Stage 5 -- spf.py:** InstrumentProfile resolution
- **Stage 6 -- placement.py:** static XYZ placement
- **Stage 7 -- gesture_engine.py:** keyframe animation and bounds
- **Stage 8 -- lusid_writer.py:** LUSID Scene API encoding
- **Stage 9A -- export/lusid_package.py:** folder export logic
- **UI -- ui/app.py:** Streamlit interface with 2D Altair Canvas for Seed Matrix

### [VALIDATED] Test Results (2026-02-11)

End-to-end test with 6 real stereo stems (96 kHz / 24-bit / ~216 seconds each):

| Stage               | Result                                           | Time  |
| ------------------- | ------------------------------------------------ | ----- |
| 0 -- Discovery      | 6 stems -> 12 objects                            | 0.4s  |
| 1 -- Normalisation  | 22 WAVs at 48 kHz (12 mono + 10 beds/LFE)        | 3.2s  |
| 2 -- MIR Extraction | 12 feature vectors extracted                     | 216s  |
| 3 -- Classification | 12 nodes classified correctly                    | <0.1s |
| 4 -- Seed Matrix    | z = [0.65 0.60 0.30 0.15 0.75 0.65 0.50 0.24]    | <0.1s |
| 5 -- SPF Resolution | 12 style profiles resolved                       | <0.1s |
| 6 -- Placement      | 12 static positions in [-1,1] cube               | <0.1s |
| 7 -- Gesture        | 488 keyframes (2 static, 10 animated)            | <0.1s |
| 8 -- LUSID Scene    | 83 frames, 488 audio-object + 10 bed/LFE entries | <0.1s |
| 9A -- Package       | 22 channels (10 silent, 12 active), 22 WAVs      | 0.7s  |

Classification accuracy (both filename and MIR-only paths produce correct results):

| Stem         | Category | Role       | Fallback | MIR-only |
| ------------ | -------- | ---------- | -------- | -------- |
| Drum Stem    | drums    | percussion | filename | drums    |
| Perc Stem    | drums    | percussion | filename | drums    |
| Bass Stem    | bass     | bass       | filename | bass     |
| Aco Stem     | guitar   | rhythm     | filename | guitar   |
| Strings Stem | strings  | rhythm     | filename | strings  |
| LV Stem      | vocals   | lead       | filename | vocals   |

### [DEFERRED] ADM Export

- **Stage 9B:** Python implementation removed. ADM authoring is explicitly delegated to `cult_transcoder`.

### [TODO] Remaining

- Additional test coverage (unit tests using `unittest` for the remainder of the modules)
- Integration of `config/defaults.json` across `src` modules to remove any hardcoded variables (such as sample rates or threshold epsilons).
- UI polish (2D Seed Matrix canvas visualization, real-time progress per stage)

### Notes on TODOs

Every module contains explicit `TODO:` comments indicating where implementation is needed, with guidance on:

- Library calls to make
- Algorithms to implement
- Data structures to populate
- Validation checks to add

## Key Contracts & Constraints (Per agents.md)

### Non-Negotiables

- Sample rate: 48 kHz
- Audio format: float32 (v1)
- No gain changes (resample only)
- Coordinate system: normalized Cartesian cube, +X=right, +Y=front, +Z=up
- Stereo stems → two objects (two groups)
- Always include beds 1-10 + LFE (silent in v1)
- Object groups start at 11
- LFE: node 4.1 → LFE.wav (special case)
- Delta frames supported (changing nodes only)
- Every source must have t=0.0 keyframe

### File Naming

- Node X.1 → X.1.wav
- Exception: node 4.1 → LFE.wav

### Output Contracts

- LUSID package at folder root (no subdirectories)
- containsAudio.json: ADM channel order (beds first, then objects)
- Channel order for ADM: 1.1, 2.1, 3.1, LFE, 5.1...10.1, then 11.1, 12.1...

### Determinism

- Lexicographic stem sorting
- Deterministic ID allocation
- Same (u,v) + inputs → identical outputs

## Next Steps

The core pipeline (Phases 1-4, 6) is complete. Remaining work:

1. **ADM export** (Phase 5 -- deferred)
   - Python implementation removed in favor of `cult_transcoder` C++ submodule.
   - Verify Logic Pro import via `cult_transcoder` CLI output.

2. **Test suite expansion** (tests/)
   - Unit tests per module
   - Edge cases (mono stems, very short stems, many stems)

3. **UI polish**
   - 2D Seed Matrix canvas visualization
   - Per-stage progress indicator during generation
   - Export download button

## Resources

- Specs: `internalDocs/*.md`
- Implementation Roadmap: `agents.md` Section 14
- LUSID: `LUSID/README.md`, `LUSID/internalDocs/*.md`
- Essentia: https://essentia.upf.edu/
- ADM: ITU-R BS.2088, EBU Tech 3364

## Quick Reference for Continuing Agents

1. `source activate.sh` (activates venv + PYTHONPATH)
2. Read `agents.md` Section 14 for the phase-by-phase roadmap
3. Phases 1-4 and 6 are done. ADM export (Phase 5) is deferred.
4. To run UI: `PYTHONPATH=. streamlit run ui/app.py`
5. To run pipeline CLI: `PYTHONPATH=. python -m src.pipeline test_session/stems`
6. To run tests: `PYTHONPATH=. python tests/test_stages_0_9.py`
7. Test at each milestone -- do not skip validation
8. Follow non-negotiables -- see `agents.md` Section 2

## License

TODO: Add license

---

Start with `agents.md` Section 14 for the complete roadmap.
