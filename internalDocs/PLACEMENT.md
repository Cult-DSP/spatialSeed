# SpatialSeed Placement Engine (Stage 6)

This document captures the current placement behavior and the improvements
implemented to make spatial layouts more mix-aware, stable, and controllable
via the Seed Matrix.

## Overview

Stage 6 takes `StyleProfile` base positions (resolved by SPF) and maps them
into final static XYZ placements in the normalized cube $[-1,1]^3$. The
placement stage is deterministic, clamp-safe, and uses the Seed Matrix style
vector to shape spread, cohesion, and depth.

## Inputs

- `StyleProfile` per node (base XYZ, category, role)
- Seed Matrix style vector $z$ (8 dims)
- `no_height` flag (forces $z=0$)
- `mir_summary` dict keyed by node_id (optional; used for depth bias)
- `manifest` session dict (optional; used for stereo pair extraction)
- `work_dir` path (optional; used to write placement audit)

## Output

- Placement dictionary: `{node_id: (x, y, z)}`
- Clamp log entries if any positions exceed cube bounds
- `work/placement_audit.json` with per-axis stats and crowding count

## Style Vector Usage (Stage 6)

|  Index | Name              | Used for                               |
| -----: | ----------------- | -------------------------------------- |
| `z[0]` | placement_spread  | XY spread scaling                      |
| `z[1]` | height_usage      | Z scaling                              |
| `z[4]` | symmetry_bias     | lateral symmetry damping               |
| `z[5]` | front_back_bias   | front vs rear Y bias                   |
| `z[6]` | ensemble_cohesion | central pull (cohesion) + density push |

## Placement Pipeline (per object)

1. **Spread + cohesion + symmetry** (XY)
2. **Height banding** (category/role bias)
3. **Height scaling** (Seed Matrix $z[1]$)
4. **Distance scaling** (radial depth shaping)
5. **Front/back bias** (Seed Matrix $z[5]$)
6. **Category-specific front curve** (additive Y bias per category)
7. **MIR depth bias** (loudness/brightness-driven Y offset)
8. **Clamp to cube** + log clamp events

## Post-processing (batch)

1. **Front-zone density control** (push non-lead sources rearward when >20 objects)
2. **Stereo pair cohesion** (shared Y/Z + minimum X separation for L/R pairs)
3. **Inter-object spacing** (lightweight repulsion with dynamic min_distance)
4. **Scene centroid normalization** (shift centroid toward (0, 0.4, 0))
5. **Clamp severity reporting** (structured warnings for excessive clamps)
6. **Placement audit** (write JSON summary to work/)

## Implemented Features

### 1. Category-aware spread

Different categories use different spatial spread multipliers:

- vocals: 0.85 / bass: 0.70 / pads: 1.15 / fx/ambience: 1.2+

### 2. Distance-aware scaling

All XYZ positions are radially scaled to preserve depth cues:

$$
distance\_factor = (0.85 + 0.3\,z_0 - 0.2\,z_6) \times category\_factor \times role\_factor
$$

### 3. Height banding

Category-specific Z offsets applied before height scaling:

- bass/drums slightly lower
- vocals mid-height
- pads/FX higher

### 4. Front-zone density control

When more than 20 objects exist, non-lead sources are gently pushed rearward
to reduce front-cluster congestion, scaled by spread and cohesion.

### 5. Inter-object spacing

A lightweight repulsion pass runs after initial placement to prevent stacking.
Uses deterministic iterative nudging and clamps back to the cube. The
`min_distance` threshold is now **dynamic** (see below).

### 6. Stereo pair cohesion

After individual placements, L/R pairs derived from the session manifest are
post-processed to share an identical Y (depth) and Z (height). A minimum X
separation of 0.15 is enforced to maintain stereo image width.

The pair map is built automatically from the manifest:
`{left_node_id: right_node_id}` for every stereo stem.

### 7. Scene centroid normalization

After all per-object and pair adjustments, the centroid of the full placement
set is shifted 50% of the way toward `(0, 0.4, 0)` to prevent global drift
and keep the mix anchored in a forward-facing listening zone.

### 8. Adaptive depth using MIR loudness/brightness

Each object receives an additive Y bias derived from its MIR features:

$$
loudness\_norm = \text{clip}\!\left(\frac{rms\_db + 60}{40}, 0, 1\right)
$$
$$
brightness\_norm = \text{clip}\!\left(\frac{centroid - 500}{5500}, 0, 1\right)
$$
$$
mir\_depth\_bias = (0.5\,loudness + 0.5\,brightness - 0.5) \times 2 \times 0.12
$$

Range: $[-0.12, +0.12]$. Loud/bright sources move forward; soft/dark move back.

### 9. Category-specific front bias curves

Additive Y offsets applied after the global front/back transform:

| Category      | Y bias |
| ------------- | ------ |
| vocals        | +0.12  |
| keys          | +0.05  |
| drums         | +0.05  |
| guitar        | +0.03  |
| strings       | +0.03  |
| bass          |  0.00  |
| pads          | -0.05  |
| sound\_design | -0.12  |
| fx            | -0.10  |
| ambience      | -0.15  |

### 10. Dynamic spacing threshold

`min_distance` scales with scene density and cohesion:

$$
min\_distance = \max\!\left(0.06,\; 0.08 \times \left(1 + 0.5\,\frac{n}{20} + 0.2\,z_6\right)\right)
$$

Scales from ~0.08 for small scenes up to ~0.15 for large, dense ones.

### 11. Clamp reporting severity

Two thresholds:
- **Count warning** (`_CLAMP_WARN_COUNT = 3`): warns if 3 or more positions are clamped.
- **Severe delta** (`_CLAMP_SEVERE_DELTA = 0.3`): logs a WARNING per event where any axis
  was clamped by more than 0.3 units; less severe events are DEBUG only.

### 12. Placement audit metrics

`write_placement_audit()` writes `work/placement_audit.json` with:

```json
{
  "object_count": 12,
  "x": {"min": -0.85, "max": 0.80, "mean": -0.02},
  "y": {"min": 0.18,  "max": 0.95, "mean": 0.62},
  "z": {"min": -0.10, "max": 0.30, "mean": 0.08},
  "crowded_pairs": 0,
  "clamped_count": 1
}
```

## Notes

- All adjustments remain deterministic; no randomness is introduced.
- Stereo pair enforcement requires the manifest to be passed into
  `compute_all_placements`. It is now wired through `pipeline.py`.
- Clamp logging remains intact for downstream diagnostics.

## Tuning & Defaults

The placement engine includes fixed multipliers defined in `PlacementEngine.__init__`:

- `category_spread_factor`: lateral spread multipliers per category.
- `category_distance_factor`: depth scaling per category.
- `category_height_bias`: Z offsets applied before height scaling.
- `role_distance_factor`: depth scaling per role (lead = closer).
- `category_front_bias`: additive Y bias per category.

Post-processing constants:

- **Front-zone push:** `push = 0.08 + 0.12 * z[0]`, scaled by cohesion.
- **Dynamic spacing:** `min_distance = max(0.06, 0.08 * (1 + 0.5*(n/20) + 0.2*z[6]))`
- **Spacing iterations:** 2 (deterministic, no randomness).
- **Centroid target:** `(0.0, 0.4, 0.0)` with strength 0.5.
- **Min stereo X separation:** 0.15.
- **MIR depth bias range:** [-0.12, +0.12].

## Debugging & Diagnostics

- Clamp events are recorded in `PlacementEngine.clamp_log`.
- Severity warnings are emitted at logger `spatialSeed.placement`.
- `work/placement_audit.json` provides a compact summary after each run.
- If placements look too clustered:
  - Increase `placement_spread` (z[0]) or decrease `ensemble_cohesion` (z[6])
  - The dynamic spacing will also increase automatically with more objects

## Performance

Inter-object spacing uses a lightweight $O(n^2)$ pass. For very large object
counts ($>200$), consider:

- reducing iterations
- skipping spacing for static objects
- spatial hashing / binning (future)

## Files

- `src/spatial/placement.py` — placement implementation
