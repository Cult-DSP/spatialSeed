# Placement Engine & Spatial Logic

The spatialization logic in SpatialSeed is handled by four main components that translate abstract user intent into concrete Cartesian coordinates.

## 1. Seed Matrix (`src/mapping/seed_matrix.py`)
Provides a high-level 2D control surface mapping `(u, v)` to an 8-dimensional style vector `z`.

| Index | Name | Influence |
| :--- | :--- | :--- |
| `z[0]` | `spread_width` | Horizontal (X) and vertical (Z) field width. |
| `z[1]` | `height_usage` | Global scaling of the Z-axis. |
| `z[2]` | `motion_intensity` | Speed and amplitude of gestures. |
| `z[3]` | `motion_complexity` | Number of keyframes and path intricacy. |
| `z[4]` | `symmetry_bias` | Enforces lateral mirror-symmetry (conservative). |
| `z[5]` | `front_back_bias` | Balance between front-facing and surround/rear placement. |
| `z[6]` | `ensemble_cohesion` | Central pull vs. density-driven repulsion. |
| `z[7]` | `modulation_sensitivity` | Strength of MIR feature coupling to motion. |

## 2. Spatial Prior Field / SPF (`src/spatial/spf.py`)
Resolves an instrument's category and role into a `StyleProfile`.

### Category Biases
| Category | Spread Factor | Distance Factor | Height Bias |
| :--- | :---: | :---: | :---: |
| **Vocals** | 0.85 | 0.90 | +0.05 |
| **Bass** | 0.70 | 0.82 | -0.12 |
| **Drums** | 0.90 | 0.90 | -0.06 |
| **Pads** | 1.15 | 1.12 | +0.12 |
| **Ambience** | 1.25 | 1.20 | +0.18 |

## 3. Placement Engine (`src/spatial/placement.py`)
Computes the static Cartesian origin for each object using a multi-step pipeline.

### Per-Object Pipeline
1. **Spread/Cohesion/Symmetry:** Scales initial X/Y based on `z[0]`, `z[6]`, and `z[4]`.
2. **Height Banding:** Applies category-specific Z offsets.
3. **Height Scaling:** Global scale by `z[1]`.
4. **Distance Scaling:** Radially scales distance from the listener:
   $$distance\_factor = (0.85 + 0.3\,z_0 - 0.2\,z_6) \times cat\_factor \times role\_factor$$
5. **Front/Back Bias:** Applies `z[5]` to push objects into the rear field.
6. **MIR Depth Bias:** Pushes loud/bright sources forward and soft/dark sources backward:
   - Loudness range: `-60dB` (back) to `0dB` (front).
   - Brightness range: `500Hz` (back) to `6000Hz` (front).
7. **Clamping:** Forces all points into the `[-1, 1]^3` cube.

### Batch Post-Processing
- **Front-Zone Density Control:** Pushes non-lead sources rearward if >20 objects exist.
- **Stereo Pair Cohesion:** Enforces identical Y/Z and a minimum X separation (0.15) for L/R pairs.
- **Inter-Object Spacing:** A deterministic repulsion pass with a dynamic threshold based on scene density.
- **Centroid Normalization:** Shifts the mix center 50% toward `(0, 0.4, 0)` to maintain forward focus.

## 4. Gesture Engine (`src/spatial/gesture_engine.py`)
Generates time-based motion keyframes.

### Motion Archetypes
- **Static:** Single keyframe at `t=0.0`.
- **Gentle Drift:** Sinusoidal wobbles around the base position. Amplitude scaled by `z[2]`.
- **Orbit:** Elliptical paths. Orbital period is synced to the extracted **tempo (BPM)** if available.
- **Reactive:** Jitter and spread modulation coupled to **Onset Density**. Higher density → more frequent motion "bursts."

### Data Optimization
The engine uses an **Emission Threshold** to filter out redundant keyframes. A new keyframe is only written if the position delta exceeds `0.01` units or spread changes more than `0.02`.
