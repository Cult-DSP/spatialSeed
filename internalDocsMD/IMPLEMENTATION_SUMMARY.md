# SpatialSeed - Implementation Summary

**Date:** 2026-02-11 (Updated)
**Status:** Skeleton structure complete with comprehensive pseudocode. Ready for prototype implementation.

## 🔥 Important for New Agents

**START HERE:**

1. Read this file (overview of what's built)
2. **Then read `agents.md` Section 14** - Complete implementation roadmap with phases
3. Follow the phase-by-phase plan in `agents.md`

**agents.md has been updated with:**

- Section 14: Detailed implementation roadmap (6 phases)
- Section 15: Resources and quick tips
- Code examples for common tasks
- Test milestones for each phase

## What Was Created

A complete repository structure for SpatialSeed with detailed pseudocode and comments based on the specifications in `internalDocsMD/`.

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
│       └── adm_bw64.py           # Stage 9B: ADM/BW64 export
├── ui/
│   └── app.py                    # Streamlit UI entry point
├── config/
│   └── defaults.json             # Default configuration
├── templates/
│   └── directSpeakerData.json    # Bed/direct-speaker template
├── cache/                        # (Created dynamically)
├── tests/                        # (Empty, ready for tests)
├── internalDocsMD/               # Design specifications (existing)
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

- Essentia feature extraction
- Per-stem summaries (loudness, centroid, flux, onset density, etc.)
- Stereo mix features (width, L/R balance)
- Hash-based caching
- mir_summary.json output

### Stage 3: Classification (src/mir/classify.py)

- Essentia models:
  - Instrument: mtg_jamendo_instrument-discogs-effnet
  - Role: fs_loop_ds-msd-musicnn
- Canonical categories: vocals, bass, drums, guitar, keys, pads, other, unknown
- Role hints: bass, rhythm, lead, percussion, fx, unknown
- Deterministic fallbacks (filename hints, MIR heuristics)
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

### Stage 9B: ADM/BW64 (src/export/adm_bw64.py)

- Calls LUSID transcoder for ADM XML
- BW64 audio interleaving (beds first, then objects)
- axml + chna chunk embedding
- Optional sidecar XML for debug

### UI (ui/app.py)

- Streamlit interface
- Seed Matrix sliders (u, v)
- Generate button
- Stem list (future: overrides)
- Results display (future)

## Implementation Status

### ✅ Complete

- Full module structure
- Comprehensive pseudocode
- Detailed comments referencing specs
- Contract documentation (agents.md compliance)
- Configuration templates
- Direct speaker template
- README and dependencies

### ⚠️ Requires Implementation

- Audio I/O (librosa/soundfile integration)
- Essentia MIR extraction
- Essentia classification models
- LUSID transcoder integration
- BW64 packaging (may need external library)
- Actual gesture generation algorithms
- UI stem list and overrides
- Test suite

### 📝 TODOs Marked Throughout

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

1. **Implement audio I/O** (session.py, audio_io.py)
   - Integrate librosa/soundfile
   - Implement resampling and stereo splitting
2. **Integrate Essentia** (mir/extract.py, mir/classify.py)
   - Load models from essentia/test/models/
   - Implement feature extraction
   - Implement classification

3. **Implement LUSID transcoder call** (export/adm_bw64.py)
   - Test LUSID submodule integration
   - Call transcoder script

4. **Implement BW64 packaging** (export/adm_bw64.py)
   - Research BW64/RF64 format libraries
   - Implement axml/chna chunk embedding

5. **Add test suite** (tests/)
   - Unit tests for each module
   - Integration tests for pipeline
   - Validation tests for outputs

6. **Complete gesture algorithms** (gesture_engine.py)
   - Implement orbit generation
   - Implement MIR-reactive motion
   - Tune keyframe thresholds

7. **Enhance UI** (ui/app.py)
   - Stem list with overrides
   - Results visualization
   - Preview player (optional)

## Resources

- Specs: `internalDocsMD/*.md`
- **Implementation Roadmap: `agents.md` Section 14** ⭐️
- LUSID: `LUSID/README.md`, `LUSID/internalDocs/*.md`
- Essentia: https://essentia.upf.edu/
- ADM: ITU-R BS.2088, EBU Tech 3364

## Next Steps

**For agents continuing this project:**

1. **Read `agents.md` Section 14** - Complete phase-by-phase implementation roadmap
2. **Follow the phases in order:**
   - Phase 1: Audio I/O (P1 - Critical)
   - Phase 2: MIR & Classification (P1 - Critical)
   - Phase 3: Spatial Processing (P2 - Core)
   - Phase 4: LUSID Output (P1 - Critical)
   - Phase 5: ADM Export (P3 - Optional)
   - Phase 6: UI & Polish (P3 - Optional)

3. **Test at each milestone** - Don't skip validation
4. **Follow non-negotiables** - See `agents.md` Section 2
5. **Use code examples** - See `agents.md` Section 14 for snippets

## License

TODO: Add license

---

**Repository ready for development!** 🚀  
**Start with `agents.md` Section 14 for the complete roadmap.**
