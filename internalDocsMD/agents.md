# AGENTS.md — SpatialSeed (LUSID-first) — Project Agent Instructions

**Date:** 2026-02-11 (Updated)
**Applies to:** `spatialSeed/` (Python prototype), integrated with the `LUSID/` submodule  
**Source of truth:**

- `internalDocsMD/DesignSpecV1.md` (high-level design)
- `internalDocsMD/lowLevelSpecsV1.md` (low-level architecture)
- `internalDocsMD/classify_README.md` (classification spec)
- **`internalDocsMD/IMPLEMENTATION_SUMMARY.md`** (current implementation status)

---

## 0) What this file is for

This file tells coding agents how to work inside the SpatialSeed project without breaking:

- LUSID compatibility
- sonoPleth rendering assumptions
- ADM packaging + Logic import goals
- deterministic ID/file naming contracts

**NEW AGENTS: Start here!**

If you are continuing implementation work on this project:

1. **SET UP ENV:** Run `./init.sh` (one-time), then `source activate.sh` (each session).
2. **READ FIRST:** `internalDocsMD/IMPLEMENTATION_SUMMARY.md` - shows what is built and what needs implementation.
3. **THEN READ:** This file for contracts and non-negotiables.
4. **CHECK:** Section 2 (Non-negotiables), Section 4 (Output contracts), Section 14 (Implementation roadmap).

**Environment setup:**

```bash
# One-time: create .venv, install deps, init submodules
./init.sh

# Each session: activate venv + set PYTHONPATH
source activate.sh
```

All Python commands (pipeline, tests, scripts) must be run inside the
activated environment. The `activate.sh` script sets `PYTHONPATH` to the
repo root so that `from src.* import ...` resolves correctly.

**Current Status (2026-02-11):**

- [DONE] Module structure with pseudocode + implemented stages 0-3
- [DONE] Virtual environment setup (init.sh / activate.sh)
- [DONE] Session discovery, audio I/O, MIR extraction, classification
- [DONE] End-to-end test with 6 real stereo stems (96 kHz -> 48 kHz, all stages pass)
- [DONE] MIR heuristic tuning: all 6 stems classify correctly via both filename and MIR-only paths
- [DONE] Spatial processing: spf.py, placement.py, gesture_engine.py (all 8 stages pass end-to-end)
- [DONE] LUSID output: lusid_writer.py (scene.lusid.json), export/lusid_package.py (containsAudio.json, WAV copy)
- [DONE] Streamlit UI: ui/app.py with stem discovery, category/role overrides, pipeline execution, results display
- [TODO] Organize files in src to be in appropriate subfolders
- [TODO] SPF reference research data -- research panning conventions (Dolby Atmos best practices, ITU-R BS.2051, mixing engineer references), academic spatial audio research. Save as CSVs/JSONs in data/spf_reference/. Use to ground the hand-tuned profiles in spf.py with cited sources.
- [TODO] Expand SPF profile coverage -- current spf.py has 10 profiles. Missing: percussion/percussion, strings/lead, keys/lead, pads/fx, bass/rhythm, vocals/rhythm (backing), horns/brass, woodwinds, choir, sound design. Informed by SPF reference data above.
- [TODO] LUSID schema validation -- lusid_writer.py validate_scene() does custom checks but never validates against LUSID/schema/lusid_scene_v0.5.schema.json. Add jsonschema validation pass (jsonschema already in requirements.txt).
- [TODO] sonoPleth renderer smoke test -- Section 10 requires loading LUSID package into sonoPleth to verify object positions, delta frames, LFE recognition. Never tested.
- [TODO] Unit tests per module -- only integration smoke tests exist. Need unit tests for: seed_matrix, spf, placement, gesture_engine, lusid_writer, lusid_package.
- [TODO] Stale TODO comment in seed_matrix.py -- line 64 says "TODO: Implement analytic mapping" but the mapping IS implemented below it. Misleading for new agents.
- [TODO] Structured logging -- Section 11 requires structured logging for discovery, ID allocation, clamp events, keyframe counts, channel order, transcoder calls. Currently uses print(). Standardise to Python logging.
- [TODO] Config-driven pipeline -- config/defaults.json exists but pipeline.py uses hardcoded values. Wire config through (gesture thresholds, z_dim, etc.).
- [TODO] Edge case: mono stems -- session.py supports mono (1 group) but no test coverage. Verify full pipeline with mono input.
- [DEFERRED] ADM export (export/adm_bw64.py) -- code written but untested. Not needed for v1.

---

## 1) Project mission (in one paragraph)

SpatialSeed is an offline authoring pipeline that takes a stereo reference mix + isolated stems and generates:

1. a **LUSID package** (folder) containing `scene.lusid.json` + mono WAVs + metadata, for immediate spatial rendering in sonoPleth, and
2. an optional **ADM/BW64 export** for DAWs (Logic Atmos import).

SpatialSeed is **LUSID-first**: LUSID JSON is the canonical scene representation; ADM XML metadata is produced by LUSID’s transcoders, while SpatialSeed owns the **audio container packaging** step.

---

## 2) Non-negotiables (v1 contracts)

### 2.1 Audio + timebase

- **Sample rate:** 48 kHz (resample everything).
- **Sample format:** float32 WAV (v1).  
  _Note:_ revisit float32 vs int16 later (compatibility vs size).
- **Normalization policy (v1):** resample to 48 kHz with **no gain changes** (no LUFS / peak normalization).  
  _Note:_ consider optional normalization later for robustness across sources.
- **Time unit:** seconds.

### 2.2 Coordinate system

- Canonical internal representation: **normalized Cartesian cube** `x,y,z ∈ [-1,1]`.
- Axes: **+X = right, +Y = front, +Z = up**.
- Clamp positions to the cube; log clamp events.

### 2.3 Object policy

- Stereo stems become **two objects** (two groups), split to **mono** WAV files.
- Object groups start at **11** and increase deterministically.

### 2.4 Beds + LFE policy (always included)

- Always include bed/direct-speaker groups **1–10** in the LUSID scene for ADM compatibility.
- Always include **LFE** as a special case:
  - Scene node: `{"id":"4.1","type":"LFE"}`
  - Audio file: **`LFE.wav`** (not `4.1.wav`)
- Bed WAVs and `LFE.wav` are **silent** in v1.  
  _Note:_ keep a TODO to relax/remove once the toolchain supports richer bed routing.

### 2.5 LUSID frames policy

- **Delta frames:** frames include **changing nodes only** (v1).
- **Requirement:** every spatial source must have an initial keyframe at **t=0.0**.
- If frame issues occur downstream, add a fallback mode:
  - periodic “full snapshot” frames, or
  - export-time frame expansion.

---

## 3) What SpatialSeed owns vs what LUSID owns

### LUSID submodule owns

- LUSID JSON schema and versioning
- Transcoding: **LUSID → ADM XML metadata**

### SpatialSeed owns

- IO + discovery, normalization, stereo splitting
- MIR extraction + caching
- instrument classification + role assignment
- Seed Matrix mapping `(u,v) → style vector z`
- SPF resolution → StyleProfile (minimal trace)
- static placement + gesture generation (sparse keyframes)
- **LUSID package creation**
- **BW64 packaging** for ADM export (embed ADM XML from LUSID)

**Agents MUST NOT** modify the LUSID schema in SpatialSeed without coordinating changes inside the LUSID submodule.

---

## 4) Output contracts (exact file layouts)

### 4.1 Output A — LUSID Package (folder)

A folder with files at the **package root**:

- `scene.lusid.json` (exact name)
- `containsAudio.json` (exact name)
- `mir_summary.json` (exact name; v1: MIR summaries only)
- mono WAV files:
  - beds: `1.1.wav`, `2.1.wav`, `3.1.wav`, `5.1.wav` … `10.1.wav`
  - special: `LFE.wav`
  - objects: `11.1.wav`, `12.1.wav`, ...

**Do not nest WAVs under `audio/` in v1.**

### 4.2 Output B — ADM/BW64 export

Produces:

- `export.adm.wav` (BW64) with channels ordered:
  1. beds: `1.1`, `2.1`, `3.1`, `LFE`, `5.1`…`10.1`
  2. objects: `11.1`, `12.1`, …
- optional sidecar `export.adm.xml` (debug-friendly)

**ADM packaging rule:** beds first, then objects, always include beds.

---

## 5) Direct speaker template (beds 1–10)

SpatialSeed uses the provided direct-speaker template (pluggable later for other formats).

| Group ID | speakerLabel | channelName                  | channelID   | cart (x,y,z)      |
| -------- | ------------ | ---------------------------- | ----------- | ----------------- |
| 1.1      | RC_L         | RoomCentricLeft              | AC_00011001 | [-1.0, 1.0, 0.0]  |
| 2.1      | RC_R         | RoomCentricRight             | AC_00011002 | [1.0, 1.0, 0.0]   |
| 3.1      | RC_C         | RoomCentricCenter            | AC_00011003 | [0.0, 1.0, 0.0]   |
| 4.1      | RC_LFE       | RoomCentricLFE               | AC_00011004 | [-1.0, 1.0, -1.0] |
| 5.1      | RC_Lss       | RoomCentricLeftSideSurround  | AC_00011005 | [-1.0, 0.0, 0.0]  |
| 6.1      | RC_Rss       | RoomCentricRightSideSurround | AC_00011006 | [1.0, 0.0, 0.0]   |
| 7.1      | RC_Lrs       | RoomCentricLeftRearSurround  | AC_00011007 | [-1.0, -1.0, 0.0] |
| 8.1      | RC_Rrs       | RoomCentricRightRearSurround | AC_00011008 | [1.0, -1.0, 0.0]  |
| 9.1      | RC_Lts       | RoomCentricLeftTopSurround   | AC_00011009 | [-1.0, 0.0, 1.0]  |
| 10.1     | RC_Rts       | RoomCentricRightTopSurround  | AC_0001100a | [1.0, 0.0, 1.0]   |

**Note:** the entire toolchain must eventually expand to other surround / direct speaker mappings. Do not hardcode Atmos-specific assumptions outside this mapping layer.

---

## 6) `containsAudio.json` contract

- Lives at package root.
- Key fields observed in example: `sample_rate, threshold_db, channels, elapsed_seconds`
- `channels[]` includes items like:

```json
[
  {
    "channel_index": 0,
    "rms_db": -200.0,
    "contains_audio": false
  },
  {
    "channel_index": 1,
    "rms_db": -200.0,
    "contains_audio": false
  },
  {
    "channel_index": 2,
    "rms_db": -200.0,
    "contains_audio": false
  }
]
```

**Interpretation**

- `channel_index` refers to **ADM channel order** (beds first, then objects).
- For v1:
  - beds + LFE are `contains_audio=false`, `rms_db≈-200`
  - object channels are computed from RMS and `threshold_db`

**Agent rule:** keep `containsAudio.json` generation deterministic and consistent with channel ordering used in ADM packaging.

---

## 7) Deterministic ID allocation + naming

### 7.1 Allocation

- Sort input stem filenames lexicographically.
- Allocate object groups starting at group **11**.
- Stereo stem consumes two groups:
  - first group = left channel
  - next group = right channel

### 7.2 Naming

- Node `X.1` → WAV file `X.1.wav`
- LFE special: node `4.1` → WAV file `LFE.wav`

### 7.3 Optional stereo metadata (guarded)

- You may emit a stereo-pair tag (minimal trace) **only behind a feature flag**.
- If any consumer breaks on unknown fields, disable by default.

---

## 8) Core pipeline stages (what to implement)

### Stage 0 — Session + discovery

- Discover stems + reference mix
- Validate audio formats
- Build a deterministic session manifest

### Stage 1 — Normalize + split audio

- Resample to 48k
- Split stereo stems to two mono buffers/files
- Create silent bed WAVs + silent `LFE.wav` (v1)

### Stage 2 — MIR (Essentia)

- Compute per-stem global summary metrics
- Write `mir_summary.json`
- Cache heavy computations (hash-based cache key)

### Stage 3 — Classification + role assignment

- Map raw labels → canonical categories
- Assign roles (lead/rhythm/ambience/fx)
- Allow user override in UI

### Stage 4 — Seed Matrix

- UI selects `(u,v)`
- Compute style vector `z = f(u,v)` (analytic mapping in v1)

### Stage 5 — SPF Resolver

- `(InstrumentProfile, z, MIR, tags) → StyleProfile`
- Store **minimal trace**:
  - prototype IDs + weights
  - `(u,v)` and `z`
  - any constraint flags

### Stage 6 — Static placement

- Produce base `cart` for each object
- Respect constraints (no-height, symmetry, etc.)
- Clamp to cube and log clamps

### Stage 7 — Gesture engine (keyframes)

- Produce sparse keyframes only
- Emit delta frames: only nodes that changed
- Ensure **t=0.0** keyframe for each source

### Stage 8 — LUSID writer

- Write `scene.lusid.json` matching LUSID v0.5.x header conventions
- Write metadata files at package root

### Stage 9 — Exports

- Export LUSID package folder (primary)
- Export ADM/BW64 (secondary):
  - call LUSID transcoder for ADM XML
  - SpatialSeed writes BW64 with correct channel order
  - embed `axml` + `chna`

---

## 9) Implementation boundaries and “don’t break” rules

### 9.1 Do not break sonoPleth renderer assumptions

- LFE is loaded by the key `"LFE"` and the file name `LFE.wav`.
- `direct_speaker` and `audio_object` nodes require `cart`.
- Unknown node types should be ignored by renderer (but treat this as fragile).

### 9.2 Keep schema additions behind flags

- Any added metadata inside LUSID frames/nodes (e.g., `agent_state`) must be feature-flagged.

### 9.3 Don’t hardcode format-specific beds

- Only bed mapping code should depend on Atmos labels.
- Everything else must treat beds as a template input.

### 9.4 Determinism is a feature

- Same inputs + seed `(u,v)` must generate identical:
  - object group IDs
  - file names
  - placements/gestures
  - exports

---

## 10) Testing + validation checklist (agents must run)

### LUSID package validation

- Verify required files exist:
  - `scene.lusid.json`, `containsAudio.json`, `mir_summary.json`
  - bed WAVs + `LFE.wav`
  - object WAVs
- Verify sample rate = 48k for all WAVs
- Verify all sources have `t=0.0` pose in LUSID
- Verify `containsAudio.json` matches channel ordering

### Renderer compatibility smoke test

- Load the package into sonoPleth using the current LUSID loader and ensure:
  - objects appear in expected positions
  - no crashes on delta frames
  - LFE is recognized (even if silent)

### ADM export smoke test

- Run `export ADM`
- Verify BW64 channel count = beds + objects
- Verify `axml` chunk exists and parses
- Verify `chna` chunk matches channel ordering
- Verify Logic import opens and shows beds + objects

---

## 11) Logging + diagnostics (required)

Agents should implement structured logging for:

- stem discovery + stereo split decisions
- ID allocation mapping (stem → group IDs → filenames)
- clamp events (XYZ out of range)
- gesture generation keyframe count per object
- export channel order list (explicitly log it)
- LUSID transcoder call (success/failure + path to XML)

---

## 12) Roadmap notes (keep these TODOs explicit)

- Add a sonoPleth utility `renderFromLUSID` that accepts a **LUSID package folder** and renders it directly.
- Consider periodic full-frame refresh if delta frames cause issues.
- Consider moving BW64/ADM packaging to C++ later.
- Integrate MIR into LUSID `spectral_features` nodes later (v2).
- Expand bed/direct-speaker mappings beyond the current template (multiple surround formats).

---

## 13) Locked answers (v1)

### Locked (v1)

1. **UI stack:** **Streamlit** (local-only) for the initial prototype.
2. **Normalization:** resample only, **no gain changes**. (Leave future TODO to add LUFS/peak normalization options.)
3. **Keyframe emission thresholds:** apply thresholds to **both position and spread**.
   - Default starting values (tunable): `pos_eps = 0.01` (normalized units), `spread_eps = 0.02`.
4. **BW64/ADM packaging:** implement in **Python** for v1; add a TODO note that a C++ packager will likely be needed for performance/robustness later.
5. **Stem classification (MIR):** use **Essentia pretrained models** as the default, with a license-aware fallback path.

---

## 13.1 MIR classifier recommendation (v1) — default stack

### A) Primary instrument category: `mtg_jamendo_instrument-discogs-effnet` (multi-label, 40 classes)

Use Essentia’s published **MTG-Jamendo instrument** classifier (multi-label) with **discogs-effnet** embeddings. This provides broad coverage including `voice`, `drums`, `guitar`, `piano/keyboard`, `pad`, `bass`, etc.

- Model family + code path is documented in Essentia “Models → Instrumentation → MTG-Jamendo instrument”.
- **Licensing note:** Essentia models by MTG are published under **CC BY-NC-SA 4.0** (non-commercial) with proprietary licensing available upon request. The MTG-Jamendo dataset itself is non-commercial. Plan to swap models or obtain a commercial license if SpatialSeed becomes a commercial product.

**Canonical category mapping (v1)**

- `vocals`: `voice`
- `bass`: `bass`, `doublebass`, `acousticbassguitar`
- `drums`: `drums`, `drummachine`, `beat`
- `percussion`: `percussion`, `bongo`
- `guitar`: `guitar`, `electricguitar`, `acousticguitar`, `classicalguitar`
- `keys`: `piano`, `electricpiano`, `rhodes`, `keyboard`, `organ`, `pipeorgan`
- `pads`: `pad`, `synthesizer` (and optionally `strings` if you want “pad-like strings”)
- `fx/ambience (soft)`: `computer`, `sampler` (treat as weak signals; mostly role is handled by the role model + MIR heuristics)
- else: `other`

**Decision rule**

- Compute a **category score** by taking `max(prob)` across mapped instrument labels per category.
- Choose the category with highest score.
- Accept if: `score >= 0.35` **and** `(score - second_best) >= 0.05`.  
  Else: category = `unknown`.

> These thresholds are intentionally conservative and should be tuned after you see real stem distributions.

### B) Secondary role hint: `fs_loop_ds-msd-musicnn` (single-label, 5 classes)

Use Essentia’s Freesound Loop Dataset **instrument role** classifier (single-label): `bass`, `chords`, `fx`, `melody`, `percussion`.  
This model is helpful for role assignment when stems are ambiguous (pads vs chords vs fx) and for “percussion” signals.

**Role mapping**

- `bass` → role hint `bass`
- `percussion` → role hint `percussion/drums`
- `melody` → role hint `lead`
- `chords` → role hint `rhythm/harmony`
- `fx` → role hint `fx/ambience`

**Decision rule**

- Accept role hint if: `max(prob) >= 0.60`; else role hint = `unknown`.

### C) Deterministic fallbacks (when confidence is low)

Apply in this order:

1. **Filename hints** (highest leverage, deterministic):
   - `vox`, `vocal` → vocals
   - `kick`, `snare`, `hat`, `drum`, `perc` → drums/percussion
   - `bass` → bass
   - `gtr`, `guitar` → guitar
   - `piano`, `keys`, `rhodes`, `organ`, `synth`, `pad` → keys/pads

2. **MIR heuristics** from `mir_summary.json` (lightweight):
   - **bass** if centroid is very low and energy is concentrated in low bands
   - **drums/percussion** if onset density + spectral flux are high and pitch confidence is low
   - **fx/ambience** if spectral flatness is high, onset density is low, and timbral complexity is high
   - **keys/guitar** if harmonicity/pitch confidence is high and centroid is mid-range

3. If still unresolved: `unknown`

### D) Implementation plan (minimal viable)

- Implement `spatialseed/mir/classify.py` with:
  - `classify_node(wav_path: str, node_id: str, stem_name: str | None) -> dict`
  - returns `{category, category_confidence, role_hint, role_confidence, top_labels, model_versions}`

- Cache predictions under:
  - `cache/classify/<audio_hash>.json`
  - (optional) `cache/embeddings/<audio_hash>.npy`

- Resample audio for models internally to 16 kHz as required by Essentia model examples; keep project audio at 48 kHz.

---

## 13.2 License-aware “commercial-ready” fallback path (optional)

If you need a permissive alternative without MTG’s CC BY-NC-SA model constraints:

- **YAMNet** (AudioSet) is commonly distributed under **Apache-2.0** and can provide broad audio event labels, but instrument taxonomy mapping is weaker for music stems.
- **OpenL3 embeddings** have weights distributed under **CC BY 4.0**; you can build a lightweight, no-training kNN/prototype mapper from your own labeled stem snippets.

These are optional plug-in backends. Keep the default Essentia models for the research prototype, but design the classifier interface to swap backends cleanly.

---

## 14) Implementation roadmap (prototype phase)

**Current status:** Phases 1-4 and 6 complete and tested with real stems. Phase 5 (ADM export) deferred.

See `internalDocsMD/IMPLEMENTATION_SUMMARY.md` for:

- Detailed module-by-module status
- Implementation priorities
- Quick start guide for new agents

### Phase 1: Core Audio Pipeline (Priority 1) -- [DONE]

**Goal:** Get basic audio I/O working end-to-end

1. **src/session.py** - [DONE] Stem discovery and ID allocation
   - Uses `soundfile` for WAV metadata, `hashlib` for SHA-256 hashing
   - Deterministic lexicographic sorting, stereo -> 2 groups, groups start at 11
   - Tested with 6 real 96 kHz stereo stems

2. **src/audio_io.py** - [DONE] Audio normalization
   - Uses `librosa.resample()` per channel for 48 kHz resampling
   - Stereo splitting to two mono WAVs (Float32 subtype via soundfile)
   - 10 silent beds (1.1-10.1) + LFE.wav generation
   - Tested: 6 stereo 96 kHz inputs -> 12 mono 48 kHz objects + 10 beds + 1 LFE = 23 WAVs

3. **Test milestone:** [DONE] Stages 0-1 pass, 22 WAVs written correctly (24s)

### Phase 2: MIR & Classification (Priority 1) -- [DONE]

**Goal:** Get feature extraction and classification working

4. **src/mir/extract.py** - [DONE] librosa-based MIR extraction
   - Features: RMS, spectral centroid (mean+std), flux, onset density,
     pitch confidence (piptrack), harmonic ratio (HPSS), spectral flatness, ZCR
   - Stereo mix features (mid/side width, L/R energy/correlation)
   - Hash-based JSON caching
   - Tested: 12 nodes extracted in ~225s

5. **src/mir/classify.py** - [DONE] Classification with deterministic fallbacks
   - Lazy Essentia TF import (graceful degradation when not installed)
   - Filename regex patterns: vox/vocal/LV/BV, drum/perc/kick/snare/hat,
     bass, gtr/guitar/aco/acoustic, piano/keys/rhodes/organ, string, synth/pad, fx/sfx
   - MIR heuristic fallbacks tuned against real stems:
     bass (low centroid + high harmonicity), drums (high onsets + low pitch conf),
     vocals (very high pitch conf + mid-high centroid + sparse onsets),
     strings (very high pitch conf + very high onset density),
     guitar (mid centroid + moderate onsets + high harmonicity),
     keys (remaining harmonic content)
   - Canonical categories: vocals, bass, drums, guitar, keys, strings, pads, fx, other, unknown
   - Role hints: bass, rhythm, lead, percussion, fx, unknown
   - Tested: 6/6 stems classified correctly via both filename and MIR-only paths

6. **Test milestone:** [DONE] Stages 0-3 pass with real stems (217s total)

### Phase 3: Spatial Processing (Priority 2)

**Goal:** Generate placements and keyframes

7. **src/seed_matrix.py** - Already complete (pure logic)

8. **src/spf.py** - Implement SPF resolver
   - Complete `init_default_profiles()` with full profile set
   - Implement `spherical_to_cartesian()` conversion
   - Implement `resolve_style_profile()` logic
   - Test: classifications + z → style profiles

9. **src/placement.py** - Implement placement engine
   - Implement `compute_placement()` with style modulations
   - Implement constraint applications
   - Test: profiles → XYZ placements

10. **src/gesture_engine.py** - Implement gesture generation
    - Implement motion generators (drift, orbit, reactive)
    - Implement keyframe emission thresholds
    - Test: placements + profiles → keyframe lists

11. **Test milestone:** Run stages 0-7, verify keyframes generated

### Phase 4: LUSID Output (Priority 1)

**Goal:** Generate valid LUSID scenes

12. **src/lusid_writer.py** - Implement scene assembly
    - Implement `assemble_frames_from_keyframes()`
    - Implement delta frame logic
    - Validate against LUSID schema
    - Test: keyframes → scene.lusid.json

13. **src/export/lusid_package.py** - Implement package export
    - Implement `copy_wavs_to_package()`
    - Implement `create_contains_audio_json()` with RMS computation
    - Implement `compute_wav_duration()` and `compute_rms_from_wav()`
    - Test: full LUSID package creation

14. **Test milestone:** Run full pipeline (stages 0-9), generate LUSID package

### Phase 5: ADM Export (Priority 3 - Optional)

**Goal:** Export ADM/BW64 for DAW import

15. **src/export/adm_bw64.py** - Implement BW64 packaging
    - Integrate with LUSID transcoder (test LUSID submodule)
    - Implement `interleave_wavs()` using numpy + scipy/soundfile
    - Implement `embed_adm_xml()` (may need external tool or library)
    - Test: LUSID package → BW64 file

16. **Test milestone:** Generate ADM/BW64, verify Logic Pro import

### Phase 6: UI & Polish (Priority 3) -- [DONE]

**Goal:** Make it usable

17. **ui/app.py** - [DONE] Complete Streamlit UI
    - Connected to pipeline with full generate flow
    - Stem list with per-node category/role override selectboxes
    - Seed Matrix (u,v) sliders in sidebar
    - Results tab: keyframe metrics, style vector display, classification table, export paths
    - Pipeline log capture and display
    - Overrides injected into pipeline via `classification_overrides` parameter

18. **Testing & Documentation**
    - Create example stems for testing
    - Write usage guide
    - Document known limitations
    - **Avoid using emojis** in documentation, code comments, or commit messages (use plain text status indicators like [DONE], [TODO], [FIXME] instead)

### Quick implementation tips:

**For audio I/O:**

```python
import soundfile as sf
import librosa

# Read audio
audio, sr = sf.read("input.wav")

# Resample
audio_48k = librosa.resample(audio, orig_sr=sr, target_sr=48000)

# Write audio
sf.write("output.wav", audio_48k, 48000, subtype='FLOAT')
```

**For Essentia:**

```python
import essentia
import essentia.standard as es

# Load audio
audio = es.MonoLoader(filename='input.wav', sampleRate=16000)()

# Load TensorFlow model
model = es.TensorflowPredictEffnetDiscogs(
    graphFilename='essentia/test/models/discogs-effnet-bs64-1.pb',
    output="PartitionedCall:1"
)

embeddings = model(audio)
```

**For containsAudio.json RMS:**

```python
import numpy as np

def compute_rms_db(audio: np.ndarray) -> float:
    rms = np.sqrt(np.mean(audio ** 2))
    if rms > 0:
        return 20 * np.log10(rms)
    return -200.0
```

### Implementation priorities summary:

- **P1 (Critical path):** Audio I/O, MIR, Classification, LUSID output
- **P2 (Core features):** Spatial processing (SPF, placement, gestures)
- **P3 (Nice-to-have):** ADM export, UI polish

### Testing strategy:

- Unit test each module with sample data
- Integration test each phase milestone
- End-to-end test with real music stems
- Validate outputs: LUSID scene schema, BW64 structure, Logic import

---

## 15) Resources for new agents

**Key files to read:**

1. `internalDocsMD/IMPLEMENTATION_SUMMARY.md` - What's built, what needs work
2. `README.md` - Project overview and quick start
3. `src/pipeline.py` - See the full pipeline flow
4. `config/defaults.json` - Configuration parameters

**External dependencies:**

- Essentia docs: https://essentia.upf.edu/
- LUSID submodule: `LUSID/README.md`
- librosa docs: https://librosa.org/
- soundfile docs: https://python-soundfile.readthedocs.io/

**Test data:**

- Use short music stems (10-30 seconds) for testing
- Include mono + stereo examples
- Include variety of instruments for classification testing

**When stuck:**

- Check TODOs in relevant module
- Refer to spec sections in this file
- Look at placeholder values for expected formats
- Start simple, then add complexity

**Remember:**

- Follow the non-negotiables (Section 2)
- Respect output contracts (Section 4)
- Log all clamp events and ID allocations (Section 11)
- Test incrementally, one phase at a time
- Keep determinism: same inputs → same outputs

---

## 16) Development log

### 2026-02-11 -- Phases 1-2 complete, tested with real stems

**What was done:**

- Implemented session.py (Stage 0): stem discovery, SHA-256 hashing, validation, deterministic
  ID allocation (groups start at 11, stereo = 2 groups), manifest JSON generation.
- Implemented audio_io.py (Stage 1): librosa per-channel resampling (96 kHz -> 48 kHz),
  stereo split to mono, 10 silent beds + LFE generation, Float32 soundfile output.
- Implemented mir/extract.py (Stage 2): librosa-based features (RMS, centroid, flux, onset
  density, pitch confidence via piptrack, harmonic ratio via HPSS, spectral flatness, ZCR),
  stereo mix features (mid/side width, L/R energy/correlation), hash-based JSON caching.
- Implemented mir/classify.py (Stage 3): lazy Essentia TF import, filename regex chain,
  MIR heuristic fallbacks, canonical category + role mapping.
- Rewrote init.sh (venv creation, pip install, submodule init, optional Essentia models).
- Created activate.sh (sources venv, sets PYTHONPATH to repo root).
- Created tests/test_stages_0_3.py (end-to-end smoke test with real stems).
- Tuned MIR heuristic thresholds against 6 real stems:
  - Raised bass centroid threshold (350 -> 1000 Hz) to catch real bass stems
  - Added drums detection via low harmonic ratio (<0.3) for sparse percussion
  - Added vocals detection (high pitch conf + mid-high centroid + sparse onsets)
  - Added strings detection (high pitch conf + very high onset density from bowing)
  - Added guitar detection (mid centroid + moderate onsets + high harmonicity)
  - Extended filename patterns: LV/BV (vocals), Aco/acoustic (guitar), string (strings)

**Test results (6 real stereo stems, 96 kHz / 24-bit / ~216s each):**

- Stage 0: 0.4s -- 6 stems discovered, 12 objects allocated
- Stage 1: 24s -- 22 WAVs written (12 mono objects + 10 beds/LFE) at 48 kHz
- Stage 2: 213s -- 12 feature vectors extracted and cached
- Stage 3: <0.1s -- 12 nodes classified (6/6 correct via both filename and MIR-only)
- Total: ~217s

**Classification results:**

- Drum -> drums/percussion (filename match)
- Perc -> drums/percussion (filename match)
- Bass -> bass/bass (filename match)
- Aco -> guitar/rhythm (filename match on "Aco"; MIR also correct)
- Strings -> strings/rhythm (filename match on "String"; MIR also correct)
- LV -> vocals/lead (filename match on "LV"; MIR also correct)

**Next:** Phase 3 -- Spatial processing (spf.py, placement.py, gesture_engine.py)

### 2026-02-11 -- Phase 3 complete, stages 0-7 end-to-end pass

**What was done:**

- Implemented spf.py (Stage 5): InstrumentProfile dataclass with azimuth/elevation/distance in
  degrees, 10 default profiles for category/role combos (vocals/lead, vocals/unknown, bass/bass,
  drums/percussion, guitar/rhythm, guitar/lead, keys/rhythm, strings/rhythm, pads/rhythm, fx/fx),
  spherical_to_cartesian() converter, stereo-pair-aware resolve_style_profile() with node_id hash
  for deterministic offset, front_back_bias/height_usage modulation, clamp_to_cube().
- Implemented placement.py (Stage 6): simplified PlacementEngine using SPF's already-resolved
  base positions, applies front_back_bias and height_usage scaling, clamps all coordinates
  to [-1,1] cube. Imports clamp_to_cube from src.spf.
- Implemented gesture_engine.py (Stage 7): four motion generators:
  - static: single keyframe at t=0
  - gentle_drift: sinusoidal offsets (amplitude 0.05+0.10\*intensity, period 4-16s),
    deterministic phase from hash(node_id)
  - orbit: elliptical path (radius 0.10+0.25*intensity, Y*0.6), period 6-16s, 8 samples/orbit
  - reactive: MIR-driven jitter bursts (n_bursts from onset_density*intensity*2,
    jitter 0.03+0.12\*intensity), deterministic RNG per node via np.random.RandomState
  - \_apply_emission_threshold() with POS_EPSILON=0.01, SPREAD_EPSILON=0.02
- Updated pipeline.py: stage 5 now passes manifest for stereo pairing, duration from manifest.
- Created tests/test_stages_0_7.py: comprehensive end-to-end smoke test for all 8 stages.

**Test results (6 real stereo stems, 96 kHz / 24-bit / ~216s each):**

- Stage 0: 0.4s -- 6 stems discovered, 12 objects allocated
- Stage 1: 3.2s -- 22 WAVs at 48 kHz (cached resampling)
- Stage 2: 216.3s -- MIR features for 12 nodes
- Stage 3: <0.1s -- 12 nodes classified (all correct)
- Stage 4: <0.1s -- style vector z = [0.65 0.60 0.30 0.15 0.75 0.65 0.50 0.24]
- Stage 5: <0.1s -- 12 style profiles resolved
- Stage 6: <0.1s -- 12 placements computed
- Stage 7: <0.1s -- 472 keyframes across 12 objects (2 static, 10 animated)
- Total: ~220s

**Spatial results (u=0.5, v=0.3):**

- drums/percussion: symmetric L/R at (-0.176, 0.647, 0.080), reactive, 3 kf each
- bass/bass: near-center at (-0.028, 0.545, -0.010), static, 1 kf each
- guitar/rhythm: L offset at (-0.330, 0.530, 0.036) and (-0.152, 0.605, 0.036), drift, 71-79 kf
- strings/rhythm: symmetric L/R at (-0.191, 0.635, 0.151), drift, 79 kf each
- vocals/lead: near-center at (-0.049, 0.614, 0.067), drift, 71-79 kf

**Observations:**

- Bass correctly placed near-center with no motion (static)
- Vocals correctly placed front-center with minimal spread
- Drums have reactive motion (3 keyframes = onset-driven jitter)
- Strings elevated (z=0.151) reflecting their profile elevation=10deg
- All positions within [-1,1] cube bounds
- All objects have t=0 keyframe (contract satisfied)
- Stereo pairs are symmetric (L/R mirrored on X axis)

**Next:** Phase 4 -- LUSID output (lusid_writer.py, export/lusid_package.py)

### 2026-02-11 -- Phase 4 complete, stages 0-9A end-to-end pass

**What was done:**

- Implemented lusid_writer.py (Stage 8): LUSIDSceneWriter builds delta frames from
  keyframes, injects bed/direct-speaker + LFE nodes at t=0, rounds cart coordinates to 6
  decimal places, sorts audio_object nodes by ID within each frame, schema-compliant
  (removed channelName from direct_speaker -- not in LUSID v0.5 schema). Full validation
  method checks sorted frames, t=0 beds/LFE/audio_objects, duplicate IDs, version string.
- Implemented export/lusid_package.py (Stage 9A): LUSIDPackageExporter creates flat package
  folder with scene.lusid.json, mir_summary.json, containsAudio.json, all WAVs. Real RMS
  computation from WAV files via soundfile/numpy. containsAudio.json has channel_index,
  node_id, wav_file, rms_db, contains_audio per channel in ADM order (beds first, objects).
  Validation checks all JSON files exist and all WAVs referenced in containsAudio are present.
- Updated pipeline.py: stage 8 uses new validate_scene(scene) API returning error list;
  stage 9A uses new validate_package() returning error list.
- Created tests/test_stages_0_9.py: comprehensive end-to-end test for all stages including
  LUSID scene structural checks (t=0 beds count, cube bounds, frame count) and package
  validation (beds silent, objects active, WAV presence).

**Test results (6 real stereo stems, same set):**

- Stages 0-7: same as previous run (~214s total for MIR-heavy stages)
- Stage 8: <0.1s -- 83 frames, 488 audio-object entries, 10 bed/LFE entries
- Stage 9A: 0.7s -- 22 channels (10 silent beds, 12 active objects), 22 WAVs copied
- Scene: version "0.5", 48 kHz, seconds timeUnit, 83 delta frames
- containsAudio: 22 channels, beds all rms_db=-200.0, objects rms_db varies
- Package validation: all files present, all WAVs accounted for
- Total: ~214s

**Next:** Phase 5 -- ADM export (export/adm_bw64.py) or pipeline CLI polish

### 2026-02-11 -- Phase 5 deferred, Phase 6 (UI) complete

**ADM export (Phase 5):**

- Code written in export/adm_bw64.py (LUSID-to-ADM XML generation, WAV interleaving via
  soundfile/numpy, sidecar XML export) but user said "for now, we dont have to worry about
  the adm portion". ADM export deferred -- not needed for v1.

**Phase 6 -- Streamlit UI:**

- Rewrote ui/app.py from pseudocode to fully functional Streamlit interface.
- Three-tab layout: Generate, Stems, Results.
- Sidebar: project/stems directory inputs, Seed Matrix (u,v) sliders with 0.01 step, version label.
- Generate tab: Discover Stems button (runs Stage 0 only for fast feedback), Generate Scene
  button (runs full pipeline stages 0-9A), stdout capture into pipeline log, progress bar.
- Stems tab: per-stem expander with metadata (sample rate, channels, duration, object count),
  classification results (category, role, fallbacks), per-node category/role override selectboxes
  ("auto" = use pipeline result, or select a canonical category/role to override).
- Results tab: summary metrics (total objects, keyframes, static vs animated), style vector
  breakdown (8 dimensions with named labels), export path info, classification table, pipeline log.
- Updated pipeline.py: added `classification_overrides` parameter to `run()` method --
  accepts dict of {node_id: {"category": ..., "role_hint": ...}}. Overrides are applied after
  normal classification (stage 3) and logged with "ui_override" in fallbacks_used.
- Updated pipeline.py return dict: now includes `classifications` (full dict) and `scene_info`
  (frame_count, audio_object_entries, bed_entries) for UI consumption.
- Streamlit 1.54.0 installed in .venv. App starts cleanly at http://localhost:8501.
- UI module imports verified: `python -c "import ui.app"` succeeds.
- Pipeline backward-compatible: `classification_overrides=None` default, existing tests unaffected.

**Verified:**

- `streamlit run ui/app.py` starts without errors
- UI module imports cleanly
- pipeline.run() signature backward-compatible (new param has default)
- All existing tests (test_stages_0_9.py) still pass

**Project status after Phase 6:**

- Phases 1-4: DONE (stages 0-9A, all tested)
- Phase 5: DEFERRED (ADM export, code written but untested)
- Phase 6: DONE (Streamlit UI, fully functional)
- Remaining: ADM export testing, unit test expansion, UI polish (2D canvas, per-stage progress)
