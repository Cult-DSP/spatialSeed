# SpatialSeed Architecture

SpatialSeed is a Python-based spatial audio authoring system. It transforms stereo stems into complex spatial scenes using a 10-stage pipeline. It is designed as a **LUSID-first** system, using the LUSID JSON schema as its canonical scene contract.

## Design Principles
- **LUSID-First:** All spatial metadata is authored to the LUSID schema.
- **Sparse Keyframes:** Motion is represented by discrete keyframes, not dense sampling.
- **Deterministic:** Given the same stems and Seed Matrix coordinates, the output is byte-identical.
- **Bounded:** All spatial coordinates are normalized and clamped to a Cartesian cube `[-1, 1]^3`.

## Coordinate System
SpatialSeed uses a normalized Cartesian coordinate system:
- **Range:** `x, y, z ∈ [-1, 1]`
- **Axes:** 
  - `+X`: Right
  - `+Y`: Front
  - `+Z`: Up
- **Origin (0,0,0):** Center of the listening space.

## Pipeline Stages

### Stage 0: Session / Discovery
- **Lexicographical Sort:** Stems are sorted by filename for deterministic ID allocation.
- **ID Allocation:** Bed channels occupy Groups 1-10. Audio objects start at **Group 11** and increment.
- **Stereo Splitting:** Stereo stems consume two consecutive Group IDs (Left then Right).

### Stage 1: Audio Normalisation
- **Sample Rate:** All audio is resampled to **48kHz float32 mono**.
- **Bed Generation:** Generates silent mono WAVs for standard 7.1.2 beds (1.1 - 10.1).
- **LFE Handling:** Special exception for Group 4.1, which maps to `LFE.wav`.

### Stage 2: MIR Extraction
- **Library:** Uses `librosa` for signal analysis.
- **Features:** Extracts RMS, spectral centroid, spectral flux, onset density, tempo, MFCCs, and pitch confidence.
- **Caching:** Results are cached in `cache/mir/` keyed by file hash.

### Stage 3: Classification
- **Multi-tier Fallback:**
  1. **ML (Essentia):** Lazy-loaded EffNet and MusicNN models.
  2. **Filename Heuristics:** Regex matching (e.g., `vox` -> `vocals`).
  3. **MIR Heuristics:** Signal-based thresholds (e.g., high onset strength -> `drums`).

### Stage 4: Seed Matrix
- **Interface:** Maps 2D `(u, v)` coordinates to an 8D style vector `z`.
- **u (0 to 1):** Aesthetic Variation (conservative → experimental).
- **v (0 to 1):** Dynamic Immersion (static → animated).

### Stage 5: SPF Resolution
- **Spatial Prior Field (SPF):** A set of instrument-aware priors (azimuth, spread, motion type).
- **Resolution:** Combines SPF priors with the style vector `z` and MIR features to create a `StyleProfile` for each object.

### Stage 6: Static Placement
- **Logic:** Produces the base `(x, y, z)` Cartesian origin.
- **Constraints:** Includes inter-object repulsion and scene centroid normalization.

### Stage 7: Gesture Generation
- **Motion:** Emits sparse keyframes based on motion archetypes (`static`, `drift`, `orbit`, `reactive`).
- **Optimization:** Only emits delta frames (nodes that changed) to minimize data bloat.

### Stage 8: LUSID Scene Assembly
- **Schema:** Formats keyframes into a LUSID Scene JSON (Version 1.0).
- **T=0:** Guarantees a keyframe for every source at time `0.0`.

### Stage 9: LUSID Package Export
- **Packaging:** Moves the scene, WAVs, and metadata (`containsAudio.json`, `mir_summary.json`) into a flat folder.

### Stage 10: ADM Export
- **External Bridge:** Invokes `cult-transcoder` to wrap the LUSID package into an ADM BWF for DAW compatibility.
