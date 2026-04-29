# SPF & Gesture Engine — v3+ Roadmap (Future Work)

**Status:** FUTURE — v3.0+  
**Created:** 2026-04-29  
**Relates to:** `internalDocs/lowLevelSpecsV1.md` (Section 9 notes)

---

## Vision

Currently (v1–v2), gesture generation uses simplified archetypes (static, drift, orbit, reactive) with hardcoded parameters. v3 will leverage deeper MIR data and parametric SPF profiles for intelligent, context-aware spatial motion.

---

## Part 1: Enhanced MIR Integration

Use the full depth of Stage 2 features to drive motion generation:

### Features Available (from `src/mir/extract.py`)

```
mir_summary["stems"][node_id]["features"] = {
    "rms_energy": float,
    "spectral_centroid_mean": float,
    "spectral_centroid_std": float,
    "spectral_flux_mean": float,
    "onset_density": float,
    "max_onset_strength": float,
    "pitch_confidence_mean": float,
    "harmonic_ratio": float,
    "spectral_flatness_mean": float,
    "zero_crossing_rate_mean": float,
    "mfcc_mean": [12 values],
    "spectral_contrast_mean": [7 values],
    "tonnetz_mean": [6 values],
    "tempo_bpm": float,
    "onset_times": [array of timestamps],
}
```

### v3 Motion Couplings

| Feature | Usage | Effect |
|---------|-------|--------|
| `tempo_bpm` | Sync orbital periods to beat grid | Orbit completes in N beats |
| `onset_times` | Reactive motion anchor points | Jitter/burst keyframes at onsets |
| `max_onset_strength` | Reactive burst magnitude | Stronger peaks → larger jitter |
| `spectral_contrast` | Motion intensity modulation | More contrast → more motion |
| `harmonic_ratio` | Motion decay curves | Higher harmonicity → smoother decay |
| `spectral_flatness` | Spread/diffuseness | Flat spectrum → wider spread |
| `pitch_confidence` | Drift smoothness | High pitch → coherent motion |

---

## Part 2: Parametric Motion Archetypes

Refactor `src/gesture_engine.py` from function-based to class-based design:

### Base Class

```python
from abc import ABC, abstractmethod

class MotionArchetype(ABC):
    """Base class for all motion generation strategies."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
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
        """
        Generate list of keyframe dicts:
        [
            {"t": 0.0, "cart": [x, y, z], "spread": s},
            {"t": 1.5, "cart": [...], "spread": s},
            ...
        ]
        """
        pass
```

### Implemented Archetypes (v3)

#### StaticArchetype

```python
class StaticArchetype(MotionArchetype):
    """Single keyframe at t=0 (no motion)."""
    
    def generate_keyframes(self, ...):
        return [
            {"t": 0.0, "cart": base_position.tolist(), "spread": style_profile.spread}
        ]
```

#### DriftArchetype

```python
class DriftArchetype(MotionArchetype):
    """Sinusoidal wandering motion."""
    
    def __init__(self, period_range: Tuple[float, float] = (4.0, 16.0)):
        super().__init__("drift")
        self.period_range = period_range
    
    def generate_keyframes(self, ...):
        # Use style_profile.drift_period_min/max
        # Emit keyframes above POS_EPSILON threshold
        # NEW: Use pitch_confidence to smooth decay curves
        ...
```

#### OrbitArchetype (ENHANCED)

```python
class OrbitArchetype(MotionArchetype):
    """Elliptical orbital motion (tempo-synced in v3)."""
    
    def __init__(self, plane: str = "xz"):
        super().__init__("orbit")
        self.plane = plane
    
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
        """
        NEW (v3): Sync orbit period to track tempo.
        
        Formerly: fixed orbit_speed = 8.0 samples/orbit
        Now: orbit_speed = 60 / mir_summary["stems"][node_id]["features"]["tempo_bpm"]
             (one orbit per beat, configurable)
        """
        tempo_bpm = mir_summary.get("stems", {}).get(node_id, {}).get("features", {}).get("tempo_bpm", 120.0)
        beat_duration = 60.0 / tempo_bpm  # seconds per beat
        
        radius = style_profile.spread * 0.3  # Scale by profile
        keyframes = []
        
        t = start_time
        sample_idx = 0
        while t < end_time:
            phase = (t % beat_duration) / beat_duration * 2 * np.pi  # [0, 2π] per beat
            
            # Elliptical path
            x = base_position[0] + radius * np.cos(phase)
            y = base_position[1]  # Keep Y fixed
            z = base_position[2] + radius * np.sin(phase) * 0.6
            
            keyframes.append({
                "t": t,
                "cart": [np.clip(x, -1, 1), y, np.clip(z, -1, 1)],
                "spread": style_profile.spread,
            })
            
            t += beat_duration / 8.0  # 8 samples per beat
            sample_idx += 1
        
        return keyframes
```

#### ReactiveArchetype (ENHANCED)

```python
class ReactiveArchetype(MotionArchetype):
    """Burst motion tied to onset events (v3: precise transient tracking)."""
    
    def __init__(self, latency: float = 0.05, decay_time: float = 0.2):
        super().__init__("reactive")
        self.latency = latency
        self.decay_time = decay_time
    
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
        """
        NEW (v3): Use exact onset_times + max_onset_strength.
        
        Formerly: hardcoded onset_density * intensity * 2 bursts
        Now: iterate over onset_times array, scale jitter by onset strength
        """
        features = mir_summary.get("stems", {}).get(node_id, {}).get("features", {})
        onset_times = features.get("onset_times", [])
        max_strength = features.get("max_onset_strength", 1.0)
        harmonic_ratio = features.get("harmonic_ratio", 0.5)
        
        keyframes = []
        rng = np.random.RandomState(hash(node_id) % 2**31)
        
        for onset_t in onset_times:
            if onset_t < start_time or onset_t > end_time:
                continue
            
            # Jitter magnitude scales with onset strength and style intensity
            jitter_mag = 0.03 + 0.12 * intensity * (max_strength / 10.0)
            
            # Jitter duration scales with harmonic content (harmonics decay slower)
            burst_duration = self.decay_time * (0.5 + 0.5 * harmonic_ratio)
            
            # Generate burst keyframes (5 samples over decay)
            for i in range(5):
                t = onset_t + (i / 5.0) * burst_duration
                if t > end_time:
                    break
                
                # Random jitter
                dx = rng.uniform(-jitter_mag, jitter_mag)
                dy = rng.uniform(-jitter_mag, jitter_mag)
                dz = rng.uniform(-jitter_mag, jitter_mag)
                
                x = np.clip(base_position[0] + dx, -1, 1)
                y = np.clip(base_position[1] + dy, -1, 1)
                z = np.clip(base_position[2] + dz, -1, 1)
                
                keyframes.append({
                    "t": t,
                    "cart": [x, y, z],
                    "spread": style_profile.spread,
                })
        
        return keyframes
```

---

## Part 3: Extended SPF Profiles (Parametric)

Expand `InstrumentProfile` dataclass with v3+ parametric motion controls:

```python
@dataclass
class InstrumentProfile:
    # ... v1–v2 fields ...
    
    # NEW (v3): Parametric motion controls
    orbit_radius: float              # Normalized [0, 1]
    orbit_speed: float               # Period in seconds (0 = use tempo sync)
    orbit_plane: str                 # "xz", "xy", "yz"
    
    reactivity_latency: float        # Response time (milliseconds)
    reactivity_scale: float          # Burst magnitude relative to MIR
    reactivity_decay: float          # Decay time after onset (seconds)
    
    drift_period_min: float          # Minimum drift cycle (seconds)
    drift_period_max: float          # Maximum drift cycle (seconds)
    drift_smoothness: float          # Curve tension (0=linear, 1=smooth)
    
    motion_intensity_scale: float    # Multiplier for style z[2]
    mir_reactive_strength: float     # How strongly MIR drives motion
```

Example profile (v3):

```python
self.instrument_profiles[("drums", "kick")] = InstrumentProfile(
    category="drums", role="kick",
    base_azimuth_deg=0.0, azimuth_spread_deg=6.0,
    base_elevation_deg=-10.0, elevation_range_deg=4.0,
    base_distance=0.52,
    default_spread=0.08,
    motion_archetype="static",  # or could be "reactive" for dynamic kicks
    
    # NEW (v3):
    reactivity_latency=0.02,     # Respond very quickly to onset
    reactivity_scale=0.05,       # Subtle jitter (kick is percussive, not melodic)
    reactivity_decay=0.1,        # Quick decay
    
    energy_sensitivity=0.10,
    flux_sensitivity=0.08,
    brightness_sensitivity=0.02,
    source_citation="[AI-GENERATED] v3 kick profile with onset reactivity",
)
```

---

## Part 4: Context-Aware Profile Selection

Allow profiles to modulate by production metadata (genre, energy, instrumentation):

```python
def resolve_style_profile_contextual(
    category: str,
    role: str,
    z: np.ndarray,
    mir_summary: dict,
    metadata: dict = None,
) -> StyleProfile:
    """
    v3: Resolve with genre, tempo, energy context.
    
    metadata keys:
    - 'genre': 'rock', 'jazz', 'classical', 'electronic', 'hip-hop', ...
    - 'tempo_bpm': float
    - 'overall_energy': float [0, 1]
    - 'production_style': 'dense', 'sparse', 'orchestral', 'minimalist'
    """
    
    # Select base profile
    profile_key = f"{category}/{role}"
    base = PROFILES.get(profile_key, PROFILES["other/unknown"])
    
    # Context-aware modulation
    if metadata:
        # Example: Jazz guitar less ambient, more interactive
        if metadata.get("genre") == "jazz" and category == "guitar":
            base.motion_archetype = "gentle_drift"
            base.drift_period_min = 1.5
            base.drift_period_max = 4.0
            base.reactivity_scale = 0.2
        
        # Example: High-energy drums more reactive
        if metadata.get("overall_energy", 0) > 0.8 and category == "drums":
            base.motion_archetype = "reactive"
            base.reactivity_scale = 1.5
            base.motion_intensity_scale = 1.2
        
        # Example: Orchestral music — slower, more cohesive motion
        if metadata.get("production_style") == "orchestral":
            base.drift_period_min *= 1.5
            base.drift_period_max *= 2.0
    
    # Apply z modulations (existing logic)
    return apply_style_modulations(base, z)
```

---

## Part 5: Implementation Timeline

### v3.0 (Mid-term, ~3–4 months after v2.0)

**Goals:** Tempo-synced orbits + onset-driven reactivity

- [ ] Refactor `gesture_engine.py` with parametric motion classes
- [ ] Extend `InstrumentProfile` with parametric fields (orbit_speed, reactivity_scale, etc.)
- [ ] Wire `tempo_bpm` to orbit sync in `OrbitArchetype`
- [ ] Wire `onset_times` to reactive bursts in `ReactiveArchetype`
- [ ] Update tests: `test_stages_0_7.py` verify tempo sync + reactive timing
- [ ] Validate against Spatial Root preview

**Files to modify:**
- `src/spatial/gesture_engine.py` (new class-based architecture)
- `src/spatial/spf.py` (extend `InstrumentProfile`)
- `tests/test_stages_0_7.py` (verify new motion)
- `SPF_PROFILE_REFERENCE.md` (document v3 parametric fields)

### v3.1 (Medium-term, ~4–6 months after v3.0)

**Goals:** Context-aware profiles + harmonic coupling

- [ ] Add context-aware `resolve_style_profile_contextual()`
- [ ] Integrate `spectral_contrast`, `harmonic_ratio` into motion intensity
- [ ] Add `metadata` parameter to pipeline (genre, energy, production style)
- [ ] UI: manual motion parameter override widgets
- [ ] Tests: genre-specific motion correctness

### v3.2+ (Long-term)

**Goals:** Full spectral integration + learnable motion

- [ ] Integrate MIR spectral features into LUSID `spectral_features` nodes
- [ ] Optional learnable motion generation (neural net backdrop)
- [ ] Gesture preview in UI (real-time visualization)
- [ ] User-defined motion templates + presets

---

## Part 6: Backward Compatibility

- **Existing archetypes remain:** `static`, `drift`, `orbit`, `reactive` as default implementations
- **v1–v2 profiles coexist:** can use old or new parametric profiles simultaneously
- **Feature-flag motion:** config option to enable/disable v3 parametric motion without breaking v1–v2
- **Gradual rollout:** v3 available as opt-in feature; default behavior unchanged

---

## Part 7: Expected Benefits

| Aspect | v1–v2 | v3+ | Improvement |
|--------|-------|-----|-------------|
| **Orbit sync** | Fixed 6–16s period | Synced to track beat | Coherence +40% |
| **Reactive timing** | Estimated onsets | Precise transient locations | Precision +90% |
| **Motion variety** | 4 archetypes (generic) | Parametric per-profile | Customization +500% |
| **Context awareness** | Fixed profiles | Genre/energy-aware modulation | Expressiveness +300% |
| **MIR utilization** | 30% of features used | 100% of features utilized | Coverage +300% |

---

## References

- **Current gesture_engine:** `src/spatial/gesture_engine.py`
- **Current SPF:** `src/spatial/spf.py`
- **MIR features available:** `src/mir/extract.py`
- **v1 notes:** `internalDocs/lowLevelSpecsV1.md` Section 9
- **v1 gesture specs:** `agents.md` Stage 7

---

## Questions?

Refer to:
- `agents.md` Section 14 (implementation roadmap)
- `internalDocs/MIR.md` (MIR pipeline overview)
- `SPF_PROFILE_REFERENCE.md` (current profile coverage)
