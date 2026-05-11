# Export Architecture & Integration

SpatialSeed ensures compatibility with the broader Cult DSP toolchain via standardized handoff contracts.

## 1. Export LUSID Package
The canonical output format. It is a flat folder designed for immediate ingestion by **Spatial Root**.

### Package Layout
```
<package_dir>/
  scene.lusid.json     # Spatial metadata (LUSID v1.0)
  containsAudio.json   # Channel mapping and RMS levels
  mir_summary.json     # Global MIR statistics
  1.1.wav              # Bed Front-Left (silent)
  ...
  4.1.wav              # LFE (Group ID 4.1)
  ...
  11.1.wav             # First Audio Object
  ...
```

### Special Case: LFE
Node ID `4.1` exists in the LUSID scene but maps specifically to `LFE.wav` (not `4.1.wav`).

## 2. Export ADM BWF
 Compatibility path for DAWs (Logic Pro, Pro Tools).
- **Delegation:** Relies on the external `cult-transcoder` submodule.
- **Channel Order:** 
  1. **Beds:** 1.1 through 10.1 (always 10 channels).
  2. **Objects:** 11.1 upward.
- **Audio:** 48kHz float32.

---

## Spatial Root Ingestion Contract

For developers building renderers (Spatial Root) that consume SpatialSeed packages:

### Audio Resolution Rules
1. **Prefer `containsAudio.json`:** Map Node IDs to filenames using the `channels` array.
2. **Deterministic Fallback:** Node `X.1` → `X.1.wav`.
3. **LFE Exception:** Node `4.1` → `LFE.wav`.

### Delta Frame Handling
SpatialSeed emits **delta frames** (changing nodes only).
- **Renderer Requirement:** The renderer must maintain a "last-known state" for all nodes.
- **Initial Pose:** Every source is guaranteed to have a keyframe at `t=0.0`.

### Validation for Renderers
1. **Sample Rate:** Assert 48kHz.
2. **Bounds:** Assert Cartesian coordinates in `[-1, 1]`. Clamp and log if outside.
3. **Completeness:** Ensure all files referenced in `containsAudio.json` exist in the package root.
