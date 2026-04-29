# Removing Essentia & Upgrading Seed Matrix / SPF

## Quick Context

You're reading this because you want to understand how to:

1. **Remove Essentia dependencies** (heavy ML model, AGPLv3 licensing, optional anyway)
2. **Upgrade the Seed Matrix** (improve `(u,v) → z` mapping)
3. **Upgrade SPF** (Spatial Prior Field — enhance placement profiles and motion archetypes)

This document provides architectural decisions and implementation patterns to guide these changes.

---

## Part 1: Removing Essentia (Classification Independence)

### Current State

**Where Essentia is used:**

- `src/mir/classify.py` — Tier 1 of fallback classification strategy
  - `mtg_jamendo_instrument-discogs-effnet` (multi-label instrument classifier)
  - `fs_loop_ds-msd-musicnn` (5-class role classifier)
  - Used **only if installed and confident results available** (lazy import)

**Current fallback chain:**

1. Try Essentia models (if available + confident) → use result
2. Else, try filename regex patterns → use result
3. Else, use MIR heuristics (librosa features) → use result

### Why You Might Remove It

| Reason                                | Impact                                          |
| ------------------------------------- | ----------------------------------------------- |
| **Licensing**: AGPLv3 (copyleft)      | Complicates commercial product distribution     |
| **Dependencies**: TensorFlow + models | Heavy install, long first-run cache download    |
| **Complexity**: ML models drift       | Need version pinning, validation, retraining    |
| **User friction**: Not always needed  | Pure librosa fallbacks are deterministic + fast |

### How to Remove It

**Step 1: Update `src/mir/classify.py`**

Simply remove the Essentia import and model loading code:

```python
# REMOVE these sections:
# - essentia_available = ... (boolean check)
# - load_essentia_models() function
# - Try/except Essentia inference blocks

# KEEP the rest:
# - Filename regex patterns
# - MIR heuristic functions
# - Three-tier fallback (just collapses to tiers 2 & 3)
```

**Before (current):**

```python
try:
    import essentia.standard as es
    essentia_available = True
except ImportError:
    essentia_available = False

def classify_node(...):
    # Try Essentia first
    if essentia_available and can_load_models():
        instrument_labels = run_essentia_instrument_classifier(...)
        if confident(instrument_labels):
            return essentia_result

    # Fall through to filename
    filename_result = apply_filename_heuristics(stem_name)
    if filename_result != "unknown":
        return filename_result

    # Fall through to MIR heuristics
    return apply_mir_heuristics(mir_summary)
```

**After (Essentia removed):**

```python
def classify_node(...):
    # Try filename first (now Tier 1)
    filename_result = apply_filename_heuristics(stem_name)
    if filename_result != "unknown":
        return filename_result

    # Fall through to MIR heuristics (now Tier 2)
    return apply_mir_heuristics(mir_summary)
```

**Step 2: Update `requirements.txt`**

Remove:

```
essentia-tensorflow>=0.1.0
essentia>=2.1.0
```

Leave in:

```
librosa>=0.10.0
numpy>=1.21.0
scipy>=1.7.0
soundfile>=0.12.0
```

**Step 3: Update `init.sh`**

Remove optional Essentia model download:

```bash
# REMOVE:
# echo "Downloading Essentia models..."
# wget https://... (model URLs)
```

**Step 4: Update Documentation**

Update `agents.md` Section 13.1 to reflect MIR-only classification:

```markdown
## 13.2 MIR-Only Classification (Essentia Removed)

After Essentia removal, the fallback chain is:

1. **Filename Heuristics** (Tier 1, deterministic regex)
   - Matches `vox`, `vocal`, `LV`, `BV` → vocals
   - Matches `drum`, `perc`, `kick`, `snare`, `hat` → drums
   - etc.

2. **MIR Heuristics** (Tier 2, librosa features)
   - Uses spectral centroid, pitch confidence, harmonic ratio, onset density
   - Tuned thresholds for bass, drums, vocals, guitar, keys, strings, pads, fx

**Verification**: Run tests/test_stages_0_3.py to ensure all stems still classify correctly.
```

**Step 5: Verify Classification Accuracy**

Run the test suite:

```bash
source activate.sh
python -m pytest tests/test_stages_0_3.py -v
```

Expected: All stems classify with correct category + role (verified against real stems in 2026-02-11 logs).

### Benefits After Removal

✅ No ML model dependency (pure NumPy/librosa)  
✅ Deterministic + reproducible (no model versioning issues)  
✅ Faster first run (no model download)  
✅ Simpler CI/CD (fewer submodules)  
✅ License-agnostic (ISC + Apache-2.0 only)  
❌ Slightly less "smart" (filename + heuristics vs learned patterns)

---

## Part 2: Upgrading the Seed Matrix

### Current State

**What it does:**

- Maps `(u,v) ∈ [0,1]²` → `z ∈ [0,1]⁸` (style vector)
- `u`: aesthetic variation (conservative → experimental)
- `v`: dynamic immersion (static → animated)

**Current mapping (analytic, v1):**

```python
def seed_matrix_mapping(u: float, v: float) -> np.ndarray:
    z1 = u              # placement_spread
    z2 = v              # height_usage
    z3 = v              # motion_intensity
    z4 = 0.2 * v       # motion_complexity
    z5 = (1 - u)       # symmetry
    z6 = 0.5 + 0.3 * u # front_back_bias
    z7 = 0.5            # ensemble_cohesion (fixed)
    z8 = u * v          # mir_coupling
    return np.array([z1, z2, z3, z4, z5, z6, z7, z8])
```

**Limitations:**

1. **Linear**: Each `z[i]` is a simple linear/bilinear combination of `(u,v)`. No curvature or interaction.
2. **Fixed ensemble_cohesion**: Always 0.5, never varies with user input.
3. **No perceptual scaling**: `u` and `v` don't account for perceptual equivalence (e.g., doubling intensity is exponential, not linear).
4. **Unused MIR coupling**: `z[7]` (mir_coupling) is computed but gesture_engine doesn't use it yet.

### Upgrade Options

#### Option A: Smooth Nonlinear Mapping

Replace linear interpolation with smooth curves (sigmoid, cubic, etc.) to create more expressive control:

```python
import numpy as np
from scipy.interpolate import interp1d

def seed_matrix_upgraded(u: float, v: float) -> np.ndarray:
    """
    Upgrade: Smooth nonlinear mapping with interaction terms.

    u: aesthetic variation [0,1]
       0 = conservative (tight, symmetric, minimal motion)
       1 = experimental (wide, asymmetric, complex motion)

    v: dynamic immersion [0,1]
       0 = static (single keyframe per object)
       1 = animated (many keyframes, reactive, orbiting)
    """

    # Smooth activation curves (sigmoid-like)
    def smooth_step(x):
        return 3*x**2 - 2*x**3  # Smoothstep (Hermite)

    def smooth_ramp(x):
        return np.tanh(2*x - 1) * 0.5 + 0.5  # Sigmoid-like

    u_smooth = smooth_ramp(u)
    v_smooth = smooth_step(v)

    # Enhanced style vector with interaction terms
    z = np.array([
        # z[0]: placement_spread (more with u, capped by v for conservative static scenes)
        u_smooth * (0.8 + 0.2 * v_smooth),

        # z[1]: height_usage (more with v, scaled by u for experimental)
        v_smooth * (0.5 + 0.5 * u_smooth),

        # z[2]: motion_intensity (primarily v, boosted by u for experimental dynamics)
        v_smooth * (0.6 + 0.4 * u_smooth),

        # z[3]: motion_complexity (only with high u AND v; avoid needless complexity)
        (u_smooth * v_smooth) ** 1.5,

        # z[4]: symmetry_breaking (more asymmetry with experimental u; v has minimal impact)
        (1 - u_smooth) * 0.8,

        # z[5]: front_back_bias (more forward with conservative u; experimentation adds variance)
        0.5 + 0.2 * (1 - u_smooth) + 0.15 * u_smooth * np.sin(3 * u),

        # z[6]: ensemble_cohesion (NOW ACTIVE; tight with v, loose with u)
        (1 - v_smooth) * (0.8 + 0.2 * (1 - u_smooth)),

        # z[7]: mir_coupling (stronger with dynamic + experimental)
        (u_smooth * v_smooth) ** 0.8,
    ])

    return np.clip(z, 0, 1)
```

**Benefits:**

- Smoother, more perceptually natural control transitions
- Interaction terms create richer expression with fewer parameters
- Ensemble cohesion now varies (tighter for static, looser for animated)

#### Option B: Data-Driven Mapping (User Studies)

Collect user preferences (place a few objects, note their spatial design intent) and fit a neural network or polynomial regression:

```python
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

def train_seed_matrix_from_user_data(user_samples: list):
    """
    user_samples: list of {u, v, z_preferred}

    Fits a polynomial regressor z = f(u, v) from real user feedback.
    """
    X = np.array([(s['u'], s['v']) for s in user_samples])
    Y = np.array([s['z_preferred'] for s in user_samples])

    poly = PolynomialFeatures(degree=3)
    X_poly = poly.fit_transform(X)

    model = LinearRegression()
    model.fit(X_poly, Y)

    return model
```

**When to use:** After releasing v1 and collecting real user sessions. Requires data collection infrastructure.

#### Option C: Analytical Upgrade (Recommended for v2)

Define the control surface analytically based on spatial audio design principles:

- **u = aesthetic**: From industry mixing practices (tight orchestrated vs. wide experimental)
- **v = dynamics**: From motion design standards (static museum display vs. responsive/animated)

Document these principles explicitly and update `internalDocs/lowLevelSpecsV1.md`:

```markdown
## Seed Matrix v2 Design Principles

### u: Aesthetic Variation

- **u = 0 (Conservative)**
  - Spread: 0.3 (tight cluster)
  - Symmetry: 0.9 (very symmetric)
  - Front-back: 0.3 (mostly front)
  - Complexity: 0.0 (no extra flourishes)
  - Ensemble: 0.9 (cohesive group)

- **u = 0.5 (Moderate)**
  - Spread: 0.5 (natural spacing)
  - Symmetry: 0.5 (balanced)
  - Front-back: 0.5 (mixed)
  - Complexity: 0.25 (modest variations)
  - Ensemble: 0.5 (some looseness)

- **u = 1 (Experimental)**
  - Spread: 0.8 (wide distribution)
  - Symmetry: 0.1 (asymmetric)
  - Front-back: 0.7 (forward-heavy or varied)
  - Complexity: 1.0 (maximized)
  - Ensemble: 0.2 (individuals shine)

### v: Dynamic Immersion

- **v = 0 (Static)**
  - Motion: None (t=0 keyframe only)
  - Height: Minimal (mostly ground level)
  - MIR reactivity: Off
  - Ensemble motion: No coordination

- **v = 0.5 (Moderate)**
  - Motion: Gentle drift/orbit (~6-16s periods)
  - Height: 50% usage
  - MIR reactivity: Weak (onsets trigger small jitters)
  - Ensemble motion: Some objects coordinated

- **v = 1 (Immersive)**
  - Motion: Multiple orbits, sweeps, reactive bursts
  - Height: Full 3D space
  - MIR reactivity: Strong (onsets trigger large motions)
  - Ensemble motion: Coordinated group choreography
```

### Implementation for Upgrade

**File to modify:** `src/seed_matrix.py`

```python
# Replace the mapping function with one of the options above
# Keep the same input signature: (u: float, v: float) -> np.ndarray

# Add docstring explaining the new design:
"""
Seed Matrix Mapping (Upgraded)

Maps user controls (u, v) to an 8-dimensional style vector z that governs
spatial layout and motion parameters across all audio objects.

Parameters:
    u (float): Aesthetic variation [0=conservative, 1=experimental]
    v (float): Dynamic immersion [0=static, 1=animated]

Returns:
    z (np.ndarray): [spread, height, motion_intensity, complexity,
                      symmetry, front_back, ensemble_cohesion, mir_coupling]
                    All values clipped to [0, 1]

References:
    - Design rationale: internalDocs/lowLevelSpecsV1.md (v2 section)
    - Used by: src/spf.py (resolve_style_profile), src/placement.py
"""
```

**Test the upgrade:**

```bash
# Update tests/test_seed_matrix.py to verify new behavior
python -m pytest tests/test_seed_matrix.py -v

# Verify gesture_engine still works with new z values
python -m pytest tests/test_stages_0_7.py -v
```

---

## Part 3: Upgrading SPF (Spatial Prior Field)

### Current State

**What it does:**

- Maintains `InstrumentProfile` objects (azimuth, elevation, distance for each category/role pair)
- Resolves profiles based on category, role, and style vector `z`
- Outputs `StyleProfile` with modulated placement + motion parameters

**Current InstrumentProfile set (10 profiles):**

```
vocals/lead, vocals/unknown, bass/bass, drums/percussion,
guitar/rhythm, guitar/lead, keys/rhythm, strings/rhythm,
pads/rhythm, fx/fx
```

**Limitations:**

1. **Limited coverage**: Only 10 category/role pairs. Missing: percussion (non-drums), choir, orchestral strings, etc.
2. **Static profiles**: No seasonal/contextual variation (e.g., "lead guitar" in a rock context vs. a jazz context)
3. **Minimal trace**: No reasoning logged about why a profile was chosen
4. **Unused parameters**: Some profiles have features that `placement.py` doesn't fully utilize

### Upgrade Options

#### Option A: Expand Category/Role Coverage

Add missing profiles:

```python
# In src/spf.py, extend init_default_profiles():

PROFILES = {
    # Existing
    "vocals/lead": InstrumentProfile(...),
    "vocals/rhythm": InstrumentProfile(...),
    "bass/bass": InstrumentProfile(...),
    ...

    # NEW: Percussion-specific
    "percussion/drums": InstrumentProfile(azimuth=0, elevation=-5, distance=2.5, motion="reactive", ...),
    "percussion/melodic": InstrumentProfile(azimuth=45, elevation=15, distance=2.0, motion="drift", ...),
    "percussion/mallet": InstrumentProfile(azimuth=-45, elevation=20, distance=2.2, motion="orbit", ...),

    # NEW: Vocal variants
    "vocals/harmony": InstrumentProfile(azimuth=±90, elevation=5, distance=2.8, motion="drift", ...),
    "vocals/ambient": InstrumentProfile(azimuth=180, elevation=30, distance=3.5, motion="gentle_drift", ...),

    # NEW: Strings
    "strings/lead": InstrumentProfile(azimuth=0, elevation=20, distance=2.0, motion="orbit", ...),
    "strings/pad": InstrumentProfile(azimuth=±120, elevation=25, distance=3.0, motion="drift", ...),

    # NEW: Woodwinds / Brass
    "woodwinds/lead": InstrumentProfile(azimuth=0, elevation=10, distance=2.5, motion="gentle_drift", ...),
    "brass/lead": InstrumentProfile(azimuth=0, elevation=15, distance=2.3, motion="orbit", ...),
    "brass/harmony": InstrumentProfile(azimuth=±45, elevation=10, distance=2.6, motion="drift", ...),

    # NEW: Synth / Electronic
    "synth/lead": InstrumentProfile(azimuth=0, elevation=0, distance=2.0, motion="orbit", ...),
    "synth/pad": InstrumentProfile(azimuth=±90, elevation=15, distance=3.0, motion="drift", ...),
    "synth/bass": InstrumentProfile(azimuth=0, elevation=-20, distance=2.5, motion="static", ...),
}
```

**Benefits:**

- Richer classification → better placement matches
- Extensible for future categories

#### Option B: Context-Aware Profile Selection

Allow profiles to be selected based on external metadata (genre, tempo, energy):

```python
def resolve_style_profile_contextual(
    category: str,
    role: str,
    z: np.ndarray,
    mir_summary: dict,
    metadata: dict = None,  # NEW: genre, bpm, energy level, etc.
) -> StyleProfile:
    """
    Resolve a StyleProfile with context awareness.

    metadata: {
        'genre': 'rock|jazz|electronic|classical',
        'tempo_bpm': float,
        'overall_energy': float,
    }
    """

    # Select base profile
    profile_key = f"{category}/{role}"
    base_profile = PROFILES.get(profile_key, PROFILES["other/unknown"])

    # Modulate based on context
    if metadata:
        if metadata.get('genre') == 'jazz' and category == 'guitar':
            # Jazz guitar: less ambient, more interactive
            base_profile.motion = "gentle_drift"  # not orbit
            base_profile.elevation = 5  # lower

        if metadata.get('overall_energy') > 0.8 and category in ['drums', 'percussion']:
            # High-energy percussion: more reactive
            base_profile.motion = "reactive"
            base_profile.motion_intensity_scale = 1.5

    # Apply z modulations (existing logic)
    return apply_style_modulations(base_profile, z)
```

**When to use:** After collecting production metadata in session.py.

#### Option C: Parametric Gesture System

Upgrade gesture_engine to use profile parameters more expressively:

```python
# In src/gesture_engine.py

class MotionArchetype:
    """Base class for all motion types."""

    def generate_keyframes(
        self,
        node_id: str,
        start_time: float,
        end_time: float,
        base_position: np.ndarray,
        style_profile: StyleProfile,
        mir_summary: dict,
        intensity: float,
    ) -> list:
        """Generate keyframes for this archetype."""
        raise NotImplementedError

class OrbitArchetype(MotionArchetype):
    def generate_keyframes(self, ...):
        # Use profile.orbit_radius, orbit_speed, orbit_plane
        # Use mir_summary.tempo_bpm to sync orbits to music beat
        pass

class ReactiveArchetype(MotionArchetype):
    def generate_keyframes(self, ...):
        # Use profile.reactivity_latency, reactivity_scale
        # Use mir_summary.onset_times to generate bursts
        pass
```

**Benefits:**

- Profiles become more expressive
- Gesture engine can leverage more MIR data (tempo, onsets)

### Recommended Upgrade Path

**v2 (near-term):**

1. Expand profiles to 20+ category/role pairs (Option A)
2. Add reasoning logs to profile selection
3. Update `internalDocs/lowLevelSpecsV1.md` with profile reference

**v3 (medium-term):**

1. Add contextual modulation (Option B + metadata from session.py)
2. Upgrade gesture engine to use profile parameters (Option C)
3. Tie in advanced MIR features (tempo_bpm, spectral_contrast) to motion

**Implementation file:** `src/spf.py`

```python
# Expand init_default_profiles()
def init_default_profiles() -> dict:
    """
    Returns a dict of {category/role: InstrumentProfile} for v2.

    v2 adds ~20 profiles for richer instrument coverage.
    Later versions can add contextual selection and parametric motion.
    """
    profiles = {
        # ... existing 10 profiles ...
        # ... add 10+ new profiles ...
    }
    return profiles

# Add profile resolution with reasoning
def resolve_style_profile(category, role, z, mir, node_id=None):
    """
    Resolve a StyleProfile with optional trace logging.

    Logs:
        - profile_key: "vocals/lead"
        - modulations_applied: ["front_back_bias=0.6", "height_scale=0.8"]
        - motion_archetype: "drift"
    """
    profile_key = f"{category}/{role}"
    base = PROFILES.get(profile_key, PROFILES["other/unknown"])

    # Log choice
    if node_id:
        logger.info(f"[{node_id}] Resolved profile: {profile_key}")

    # Apply z modulations
    result = apply_style_modulations(base, z)

    return result
```

---

## Implementation Checklist

### Remove Essentia

- [ ] Delete Essentia import block in `src/mir/classify.py`
- [ ] Remove `essentia-tensorflow` from `requirements.txt`
- [ ] Remove Essentia model download from `init.sh`
- [ ] Update `agents.md` Section 13.1 → 13.2
- [ ] Run `pytest tests/test_stages_0_3.py -v` → verify classification still works
- [ ] Update README.md (remove Essentia from dependencies section)

### Upgrade Seed Matrix

- [ ] Choose upgrade option (A: smooth nonlinear, B: data-driven, C: analytical)
- [ ] Implement new mapping in `src/seed_matrix.py`
- [ ] Add comprehensive docstring + references
- [ ] Update tests: `pytest tests/test_seed_matrix.py -v`
- [ ] Run full pipeline: `pytest tests/test_stages_0_9.py -v`
- [ ] Document new z-vector semantics in `internalDocs/lowLevelSpecsV1.md`

### Upgrade SPF

- [ ] Choose upgrade option (A: coverage, B: context, C: parametric)
- [ ] Implement in `src/spf.py`
- [ ] Add profile reference table in `internalDocs/lowLevelSpecsV1.md`
- [ ] Add reasoning logs to `resolve_style_profile()`
- [ ] Run full pipeline: `pytest tests/test_stages_0_9.py -v`
- [ ] (Optional) Enhance gesture_engine for new parameters

### Documentation

- [ ] Update `agents.md` with new architecture
- [ ] Update `internalDocs/lowLevelSpecsV1.md` with design rationale
- [ ] Update `README.md` dependencies section
- [ ] Add comment headers to all modified functions

---

## Resources

**Current state:**

- Agents: `internalDocs/agents.md` (Section 13.1 for Essentia, Section 14 for roadmap)
- MIR: `internalDocs/MIR.md` (detailed pipeline overview)
- Implementation: `IMPLEMENTATION_SUMMARY.md`

**To implement:**

1. **Essentia removal**: Start with `src/mir/classify.py` (1-2 hour task)
2. **Seed Matrix upgrade**: Start with `src/seed_matrix.py` (2-4 hour task depending on complexity)
3. **SPF upgrade**: Start with `src/spf.py` (3-6 hour task depending on scope)

**Testing:**

```bash
source activate.sh

# After Essentia removal:
pytest tests/test_stages_0_3.py -v

# After Seed Matrix upgrade:
pytest tests/test_seed_matrix.py -v
pytest tests/test_stages_0_9.py -v

# After SPF upgrade:
pytest tests/test_stages_0_9.py -v
```

**When in doubt:**

- Check `agents.md` non-negotiables (Section 2)
- Check output contracts (Section 4)
- Run full end-to-end pipeline after each change
- Verify LUSID package still produces valid scenes

---

## Questions?

If you're stuck:

1. **Essentia-related**: See `src/mir/classify.py` current code + `internalDocs/MIR.md`
2. **Seed Matrix design**: See `internalDocs/lowLevelSpecsV1.md` + `src/seed_matrix.py`
3. **SPF design**: See `internalDocs/lowLevelSpecsV1.md` + `src/spf.py`
4. **Architecture**: See `agents.md` Section 3 ("What SpatialSeed owns vs what LUSID owns")

Good luck! 🚀
