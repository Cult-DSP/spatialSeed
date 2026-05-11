# Placement Engine & Spatial Logic

The spatialization logic in SpatialSeed is handled by four main components:

## 1. Seed Matrix (`src/mapping/seed_matrix.py`)
Provides a high-level 2D control surface:
- `u` [0,1]: Aesthetic Variation (conservative → experimental).
- `v` [0,1]: Dynamic Immersion (static → enveloping/animated).
Maps non-linearly to an 8-dimensional style vector `z`.

## 2. Spatial Prior Field / SPF (`src/spatial/spf.py`)
Maintains base profiles for instrument categories and roles (e.g., `vocals/lead`, `drums/percussion`).
- Resolves a `StyleProfile` per object by combining the base SPF profile, `z` vector, and deep MIR features.
- Uses deterministic metadata tags and stereo pairings.

## 3. Placement Engine (`src/spatial/placement.py`)
Computes the static Cartesian origin for each object.
- **Constraints:** Clamps all positions to a normalized `[-1, 1]^3` cube.
- **Cohesion:** Maintains stereo pairs and dynamically repels crowded objects.
- **MIR Depth Bias:** Pushes loud/bright sources forward (+Y) and soft/dark sources backward (-Y).

## 4. Gesture Engine (`src/spatial/gesture_engine.py`)
Adds time-based motion.
- Generates sparse keyframes based on the `motion_type` defined in the `StyleProfile` (`static`, `gentle_drift`, `orbit`, `reactive`).
- Limits data output by only emitting delta frames when positions change past a defined threshold.
