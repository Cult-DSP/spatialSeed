# SpatialSeed — High-Level Design Specification (LUSID-first) v1.0

**Date:** 2026-02-10  
**Status:** Updated to make LUSID the canonical scene output; ADM export is a downstream package step.

---

## 1. Purpose

SpatialSeed is an offline authoring tool that generates **immersive spatial scene data** from:

- a stereo reference mix
- isolated stems

Its primary output is a **LUSID scene + audio package** suitable for rapid spatial rendering in sonoPleth, plus an optional **ADM/BW64 export** for DAWs (Logic Atmos import).

---

## 2. Core concepts

### 2.1 Spatial Prior Field (SPF)

A curated, deterministic set of instrument-aware spatial priors:

- base placement tendencies (azimuth/elevation behavior translated into normalized XYZ)
- spread/diffuseness preferences
- motion archetype defaults
- modulation sensitivities (energy/flux/brightness → motion)

SPF is not ML-trained in v1; it is designed to be interpolatable and future-proof for learned priors later.

### 2.2 Seed Matrix Interface

A 2D control surface:

- **u axis:** aesthetic variation (conservative → experimental)
- **v axis:** dynamic immersion (static → enveloping / animated)

The selected point `(u,v)` is mapped to a low-dimensional style vector `z = f(u,v)` used across all instruments.

---

## 3. System outputs

### 3.1 Output A — LUSID Package (primary)

A folder containing:

- `scene.lusid.json` (LUSID Scene v0.5.x conventions)
- mono WAVs named `X.Y.wav` (beds + objects) and `LFE.wav`
- `containsAudio.json` (silence flags; beds are silent in v1)
- `mir_summary.json` (v1: external MIR summaries; future: LUSID spectral_features)

This package is intended to be **drop-in renderable** by sonoPleth (planned helper: `renderFromLUSID`).

### 3.2 Output B — ADM/BW64 export (secondary)

SpatialSeed exports BW64 with embedded ADM XML:

- LUSID provides: **LUSID → ADM XML**
- SpatialSeed provides: **audio packaging** (BW64 + embed `axml` + `chna`)

Channel order: **beds first, then objects**, always include beds (silent in v1).

---

## 4. Pipeline overview

1. **Input & Session Manager**

- discovers stems
- normalizes audio (48 kHz)
- splits stereo stems to two mono objects

2. **MIR Extraction (Essentia)**

- per-stem features (loudness, centroid, flux, onset density, etc.)
- stereo mix features (width, LR energy)

3. **Instrument Classification & Role Assignment**

- classifier predicts category
- heuristics assign role (lead/rhythm/ambience/fx)
- user override allowed (UI)

4. **Seed Matrix Selection**

- user selects `(u,v)`
- system computes style vector `z`

5. **Profile Resolution**

- SPF + `z` + MIR + tags → per-object StyleProfile
- minimal trace stored for reproducibility (prototype ids + weights + z)

6. **Static Placement**

- StyleProfile + mix features → base normalized XYZ placement per object

7. **Gesture Engine**

- generates sparse keyframes (delta frames supported)
- motion intensity governed by Seed Matrix `v` axis

8. **LUSID Scene Assembly**

- writes `scene.lusid.json` (canonical representation)

9. **Exports**

- LUSID package folder
- optional ADM/BW64 via LUSID transcoder + SpatialSeed packager

---

## 5. Compatibility and constraints (v1)

- Internal coordinates in normalized cube `[-1,1]^3` using:
  - +X right, +Y front, +Z up
- Sparse keyframes only (no dense trajectories).
- Stereo stems become two objects (two groups) and are split to mono WAVs.
- Beds are included for ADM compatibility and are silent in v1 (tracked as a removable constraint later).
- Audio format: 48 kHz, float32 (v1; revisit later).

---

## 6. Minimal UI (local)

A minimal local web UI supports:

- Seed Matrix control (u,v)
- stem list + category/role overrides
- generate + export buttons
- (optional) preview and diagnostics

Implementation can start lightweight and local-only.

---

## 7. Future work (explicit)

- Upgrade performance-critical packaging/render paths to C++.
- Replace analytic `f(u,v)` with learned latent spaces while preserving Seed Matrix UX.
- Integrate MIR into LUSID spectral_features nodes.
- Expand direct speaker mappings for non-Atmos bed sets and other environments.
- Introduce explicit LFE/sub bus routing and multi-sub support (deferred).
- Add `renderFromLUSID` interface inside sonoPleth to load and render the LUSID package directly.
