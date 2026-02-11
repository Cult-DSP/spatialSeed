# SpatialSeed — Low-Level Systems Architecture (LUSID-first) v1.0

**Date:** 2026-02-10  
**Status:** Locked (per current conventions + provided renderer behavior)

---

## 0. Core decisions

- **Python-first prototype** (Essentia MIR).  
  **Note:** Plan a future C++ upgrade for performance-critical parts (BW64/ADM writer, heavy DSP, possibly preview).
- Motion is **sparse keyframes** only (no dense sampling).
- Internal spatial representation: **normalized Cartesian cube** `x,y,z ∈ [-1, 1]`.
- Coordinate convention: **+X = right, +Y = front, +Z = up**.
- Stereo stems → **two object groups** (split to mono WAVs).
- Export priorities:
  1. **LUSID Package** for sonoPleth quick render
  2. **ADM/BW64** for Logic import (beds first, then objects; always include beds)
- LFE: special file **`LFE.wav`** (always present; silent in v1).
- Audio format: **48 kHz**, mono, **float32** (v1).  
  **Note:** revisit float32 vs int16 later.

---

## 1. Responsibilities and ownership

### LUSID submodule owns

- LUSID scene JSON schema (Scene v0.5.x)
- Transcoding: **LUSID scene → ADM XML metadata**

### SpatialSeed owns

- Session + IO + normalization + stereo splitting
- MIR extraction (Essentia) + caching
- instrument classification + role assignment
- Seed Matrix mapping `(u,v) → style vector z`
- SPF resolution → per-object StyleProfile (minimal trace)
- static placement + gesture generation (keyframes)
- **LUSID package creation** (scene + WAVs + metadata)
- **BW64 packaging** for ADM export (embed ADM XML from LUSID transcoder)

---

## 2. Outputs

### 2.1 LUSID Package (folder)

A folder containing:

- `scene.lusid.json` (boilerplate name)
- `containsAudio.json` (package root)
- `mir_summary.json` (package root, v1: summaries only)
- mono WAV files named by node id, plus `LFE.wav`

**Layout**

```
<export_dir>/
  scene.lusid.json
  containsAudio.json
  mir_summary.json
  1.1.wav
  2.1.wav
  3.1.wav
  LFE.wav
  5.1.wav
  6.1.wav
  7.1.wav
  8.1.wav
  9.1.wav
  10.1.wav
  11.1.wav
  12.1.wav
  ...
```

**Notes**

- Bed WAVs (`1.1..10.1` and `LFE.wav`) are **silent** in v1 for ADM compatibility.  
  Note to remove/relax this later once the toolchain supports richer mappings.
- Future: expand the “direct speaker mapping” beyond the current template.

### 2.2 ADM export (BW64 + ADM XML)

Produces:

- `export.adm.wav` (BW64) with channels ordered:
  1. beds (1.1, 2.1, 3.1, LFE.wav, 5.1…10.1)
  2. objects (11.1, 12.1, …)
- optionally `export.adm.xml` sidecar (debug)

SpatialSeed packaging flow:

1. call LUSID transcoder: `scene.lusid.json → ADM XML`
2. interleave mono WAVs in the bed-first channel order
3. write BW64 + embed `axml` (ADM XML) + `chna` mappings

---

## 3. LUSID scene contract (Scene v0.5.x)

### 3.1 Scene header (v1)

- `version`: match the agent doc conventions (Scene “0.5” field value)
- `sampleRate`: 48000
- `timeUnit`: `"seconds"`

### 3.2 Frames: delta frames are allowed (v1)

Frames contain **changing nodes only**.

Why this is compatible: the renderer builds **per-source keyframe lists** based on occurrences in frames (node omissions simply mean “no keyframe at that time”).  
**Requirement:** every spatial source must have a keyframe at `t=0.0` (initial pose), otherwise it is undefined until its first appearance.

**Note:** If frame issues occur, investigate periodic refresh frames or full snapshots.

### 3.3 Node types emitted

SpatialSeed writes nodes of types:

- `direct_speaker` — bed channels (always at time 0)
- `audio_object` — stems and split stereo channels
- `LFE` — special node id `4.1`, no `cart`, creates renderer key `"LFE"`

It may also write trace nodes (renderer ignores):

- `agent_state` (minimal trace only, optional flag)
- (future) `spectral_features` (omitted in v1)

---

## 4. Direct speaker template (beds 1–10)

Direct speaker mapping is defined by the provided `directSpeakerData.json`. This is treated as a **pluggable template** and must expand to other mappings later.

| Group ID | speakerLabel | channelName                  | channelID   | cart              |
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

**LFE special case**

- LUSID scene includes: `{ "id": "4.1", "type": "LFE" }`
- Audio file is `LFE.wav` (silent in v1)
- In renderer, LFE is keyed as `"LFE"` (not `"4.1"`).

---

## 5. containsAudio.json (package root)

SpatialSeed writes `containsAudio.json` at the **package root**, using the provided schema.

Example excerpt:

```json
{
  "sample_rate": 48000,
  "threshold_db": -100,
  "channels": [
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
    },
    {
      "channel_index": 75,
      "rms_db": -96.45,
      "contains_audio": true
    }
  ],
  "elapsed_seconds": 2.48
}
```

**Interpretation**

- `channel_index` corresponds to **ADM/BW64 channel order** (beds first, then objects).
- Bed channels and `LFE.wav` are marked `contains_audio=false` in v1.
- Object channels are computed from RMS vs `threshold_db`.

---

## 6. Deterministic ID + filename allocation

### 6.1 Stem ordering

- Sort stems by **filename** (stable).
- Allocate objects from group `11` upward.
- Stereo stem consumes **two groups** (L then R), and is split to mono WAVs.

### 6.2 Naming rules

- `X.1` nodes map to `X.1.wav`
- `4.1` (LFE node) maps to `LFE.wav` (special exception)

### 6.3 Optional stereo pair tag (guarded)

- May add a lightweight `agent_state` tag to mark linked stereo pairs.  
  **Note:** keep behind a config flag because unknown fields can break strict consumers.

---

## 7. Pipeline phases (module-level)

1. Session + discovery
2. Normalize audio (48k) + stereo split → mono buffers
3. MIR extract (Essentia) + cache
4. Classify + role assign
5. Seed matrix `(u,v) → z`
6. SPF resolve → StyleProfile (+ minimal trace)
7. Static placement (XYZ)
8. Gesture generation (sparse keyframes)
9. Assemble + write `scene.lusid.json`
10. Export:

- LUSID package folder (mono WAVs + metadata)
- ADM export (call LUSID transcoder → ADM XML; package into BW64)

---

## 8. SonoPleth integration note

Add a sonoPleth entrypoint:

- `renderFromLUSID` that accepts a **LUSID package folder** and renders directly.

Responsibilities:

- load `scene.lusid.json`
- validate presence of required WAVs (including `LFE.wav`)
- run the standard spatial rendering pipeline

---

## 9. Notes for future revisions

- Verify whether all consumers support delta frames robustly; if not, add snapshot mode.
- Evaluate distance (radius) vs spread/diffuseness perceptually.
- Expand direct speaker templates beyond the current “room-centric” mapping.
- Integrate MIR into LUSID `spectral_features` nodes later.
- Revisit audio sample format (float32 vs int16) for compatibility + size.
