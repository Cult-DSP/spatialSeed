# SpatialSeed Architecture

SpatialSeed is a Python-based spatial audio authoring system. It transforms stereo stems into complex spatial scenes using a 10-stage pipeline.

## Pipeline Stages

0. **Session / Discovery:** Scans the `stems` directory, allocates deterministic object IDs, and builds a session manifest.
1. **Audio Normalisation:** Resamples audio to 48kHz (float32) and splits stereo files into dual mono. Generates silent beds (1.1-10.1) and LFE.
2. **MIR Extraction:** Analyzes audio features using `librosa` (RMS, spectral centroid, spectral flux, pitch confidence, tempo, etc.).
3. **Classification:** Uses filename heuristics and fallback MIR heuristics to assign an instrument `category` and `role_hint`.
4. **Seed Matrix:** Takes user parameters `u` (aesthetic variation) and `v` (dynamic immersion) and maps them to an 8-dimensional style vector `z`.
5. **SPF Resolution:** Uses the Spatial Prior Field (SPF) to map classifications and the `z` vector into a `StyleProfile` for each object.
6. **Static Placement:** Computes initial `(x, y, z)` Cartesian coordinates within a normalized cube `[-1, 1]^3`.
7. **Gesture Generation:** Adds motion (static, drift, orbit, reactive) by emitting sparse keyframes for each object.
8. **LUSID Scene Assembly:** Converts keyframes into delta frames according to the LUSID schema v1.0.
9. **LUSID Package Export:** Packages the `scene.lusid.json`, `containsAudio.json`, and all WAV files into a canonical folder.
10. **ADM Export (via CULT):** Optional step. Invokes the external `cult-transcoder` binary to generate ADM BWF and ADM XML from the LUSID package.

## Core Dependencies
- `librosa`: Deep MIR extraction.
- `soundfile`: Audio IO.
- `numpy`: Fast mathematical operations for placement/gestures.
- `streamlit`: GUI.
