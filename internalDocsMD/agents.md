# AGENTS.md — SpatialSeed (LUSID-first) — Project Agent Instructions
**Date:** 2026-02-10
**Applies to:** `sonoPleth/spatialseed/` (Python prototype), integrated with the `LUSID/` submodule  
**Source of truth:**  
- `SpatialSeed_LowLevel_Architecture_LUSIDFirst_v1.md`  
- `SpatialSeed_DesignSpec_LUSIDFirst_v1.md`

---

## 0) What this file is for

This file tells coding agents how to work inside the SpatialSeed project without breaking:
- LUSID compatibility
- sonoPleth rendering assumptions
- ADM packaging + Logic import goals
- deterministic ID/file naming contracts

If you are about to implement a feature, start by reading:
1) **Non-negotiables** (Section 2)  
2) **Output contracts** (Section 4)  
3) **Pipeline + module boundaries** (Section 5)

---

## 1) Project mission (in one paragraph)

SpatialSeed is an offline authoring pipeline that takes a stereo reference mix + isolated stems and generates:
1) a **LUSID package** (folder) containing `scene.lusid.json` + mono WAVs + metadata, for immediate spatial rendering in sonoPleth, and  
2) an optional **ADM/BW64 export** for DAWs (Logic Atmos import).  

SpatialSeed is **LUSID-first**: LUSID JSON is the canonical scene representation; ADM XML metadata is produced by LUSID’s transcoders, while SpatialSeed owns the **audio container packaging** step.

---

## 2) Non-negotiables (v1 contracts)

### 2.1 Audio + timebase
- **Sample rate:** 48 kHz (resample everything).
- **Sample format:** float32 WAV (v1).  
  *Note:* revisit float32 vs int16 later (compatibility vs size).
- **Normalization policy (v1):** resample to 48 kHz with **no gain changes** (no LUFS / peak normalization).  
  *Note:* consider optional normalization later for robustness across sources.
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
  *Note:* keep a TODO to relax/remove once the toolchain supports richer bed routing.

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
  1) beds: `1.1`, `2.1`, `3.1`, `LFE`, `5.1`…`10.1`
  2) objects: `11.1`, `12.1`, …
- optional sidecar `export.adm.xml` (debug-friendly)

**ADM packaging rule:** beds first, then objects, always include beds.

---

## 5) Direct speaker template (beds 1–10)

SpatialSeed uses the provided direct-speaker template (pluggable later for other formats).

| Group ID | speakerLabel | channelName | channelID | cart (x,y,z) |
|---|---|---|---|---|
| 1.1 | RC_L | RoomCentricLeft | AC_00011001 | [-1.0, 1.0, 0.0] |
| 2.1 | RC_R | RoomCentricRight | AC_00011002 | [1.0, 1.0, 0.0] |
| 3.1 | RC_C | RoomCentricCenter | AC_00011003 | [0.0, 1.0, 0.0] |
| 4.1 | RC_LFE | RoomCentricLFE | AC_00011004 | [-1.0, 1.0, -1.0] |
| 5.1 | RC_Lss | RoomCentricLeftSideSurround | AC_00011005 | [-1.0, 0.0, 0.0] |
| 6.1 | RC_Rss | RoomCentricRightSideSurround | AC_00011006 | [1.0, 0.0, 0.0] |
| 7.1 | RC_Lrs | RoomCentricLeftRearSurround | AC_00011007 | [-1.0, -1.0, 0.0] |
| 8.1 | RC_Rrs | RoomCentricRightRearSurround | AC_00011008 | [1.0, -1.0, 0.0] |
| 9.1 | RC_Lts | RoomCentricLeftTopSurround | AC_00011009 | [-1.0, 0.0, 1.0] |
| 10.1 | RC_Rts | RoomCentricRightTopSurround | AC_0001100a | [1.0, 0.0, 1.0] |

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
1) **UI stack:** **Streamlit** (local-only) for the initial prototype.  
2) **Normalization:** resample only, **no gain changes**. (Leave future TODO to add LUFS/peak normalization options.)  
3) **Keyframe emission thresholds:** apply thresholds to **both position and spread**.  
   - Default starting values (tunable): `pos_eps = 0.01` (normalized units), `spread_eps = 0.02`.  
4) **BW64/ADM packaging:** implement in **Python** for v1; add a TODO note that a C++ packager will likely be needed for performance/robustness later.  
5) **Stem classification (MIR):** use **Essentia pretrained models** as the default, with a license-aware fallback path.

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

1) **Filename hints** (highest leverage, deterministic):  
   - `vox`, `vocal` → vocals  
   - `kick`, `snare`, `hat`, `drum`, `perc` → drums/percussion  
   - `bass` → bass  
   - `gtr`, `guitar` → guitar  
   - `piano`, `keys`, `rhodes`, `organ`, `synth`, `pad` → keys/pads  

2) **MIR heuristics** from `mir_summary.json` (lightweight):  
   - **bass** if centroid is very low and energy is concentrated in low bands  
   - **drums/percussion** if onset density + spectral flux are high and pitch confidence is low  
   - **fx/ambience** if spectral flatness is high, onset density is low, and timbral complexity is high  
   - **keys/guitar** if harmonicity/pitch confidence is high and centroid is mid-range  

3) If still unresolved: `unknown`

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
