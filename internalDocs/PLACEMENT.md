# SpatialSeed Placement Engine (Stage 6)

This document captures the current placement behavior and the improvements
implemented to make spatial layouts more mix-aware, stable, and controllable
via the Seed Matrix.

## Overview

Stage 6 takes `StyleProfile` base positions (resolved by SPF) and maps them
into final static XYZ placements in the normalized cube $[-1,1]^3$. The
placement stage is deterministic, clamp-safe, and uses the Seed Matrix style
vector to shape spatial spread, cohesion, and depth.

## Inputs

- `StyleProfile` per node (base XYZ, category, role)
- Seed Matrix style vector $z$ (8 dims)
- `no_height` flag (forces $z=0$)

## Output

- Placement dictionary: `{node_id: (x, y, z)}`
- Clamp log entries if any positions exceed cube bounds

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
6. **Clamp to cube** + log clamp events

## Implemented Improvements

### 1. Category-aware spread

Different categories use different spatial spread multipliers to keep lead
elements tighter while letting pads/FX breathe.

Example multipliers:

- vocals: 0.85
- bass: 0.70
- pads: 1.15
- fx/ambience: 1.2+

### 2. Distance-aware scaling

All XYZ positions are radially scaled to preserve depth cues:

$$
distance\_factor = (0.85 + 0.3\,z_0 - 0.2\,z_6) \times category\_factor \times role\_factor
$$

### 3. Height banding

Category-specific Z offsets are applied before height scaling to create a
stable vertical mix hierarchy:

- bass/drums slightly lower
- vocals mid-height
- pads/FX higher

### 4. Front-zone density control

When many objects exist, non-lead sources are gently pushed rearward to
reduce front-cluster congestion, scaled by spread and cohesion.

### 5. Inter-object spacing

A lightweight repulsion pass runs after initial placement to prevent objects
stacking at identical coordinates. It uses deterministic, iterative nudging
and clamps results back to the cube.

## Notes

- Stereo pair enforcement is not enabled yet because pair metadata is not
  currently carried into `StyleProfile` traces.
- All adjustments remain deterministic; no randomness is introduced.
- Clamp logging remains intact for downstream diagnostics.

## Files

- `src/spatial/placement.py` — placement implementation
