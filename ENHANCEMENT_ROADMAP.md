# SpatialSeed Mixing Engine — Enhancement Roadmap (v2.2+)

**Status:** Current system fully functional (Stage 0-9A complete)  
**Focus:** Next-generation improvements for spatial mixing quality, efficiency, and user experience

---

## 🎯 High-Impact Priorities

### Priority 1: Adaptive MIR-Driven Mixing (High Impact, Medium Effort)

**Current State:** MIR features extracted but underutilized in spatial mapping

**Proposed Enhancements:**

#### 1.1 Dynamic Stereo Width Detection

```python
# In Stage 5 (SPF Resolution)
# Detect if stem is stereo-encoded and extract width

from librosa import effects

def extract_stereo_width(stem_id, mir_summary):
    """
    Analyze L/R correlation to determine stereo width.

    Returns:
    - width_score: 0 (mono-like) to 1 (wide stereo)
    - lr_correlation: Pearson correlation (-1 to 1)
    - stereo_imaging: perceptual width estimate
    """
    # Use spectral_contrast + energy asymmetry
    # Apply to azimuth_spread in StyleProfile
```

**Impact:** Better width preservation for stereo stems, prevents artificial narrowing  
**User Benefit:** Stereo images sound more natural and spacious

#### 1.2 Energy-Adaptive Elevation

```python
# In Stage 7 (Gesture Engine)
# Elevation subtly follows energy envelope

def adaptive_elevation_keyframes(profile, mir_summary, stem_id, duration):
    """
    Modulate base_elevation by RMS energy curve.

    - Quiet sections: drop elevation slightly (closer to ear level)
    - Loud sections: raise elevation (more enveloping)
    - Fade-out: gentle descent to minimal height
    """
    energy = mir_summary["stems"][stem_id]["features"]["rms_energy"]
    # Apply gentle smoothing: max ±5° modulation
```

**Impact:** Immersive mix that "breathes" with energy dynamics  
**User Benefit:** More engaging spatial presentation

#### 1.3 Spectral Contrast → Brightness Modulation

```python
# In Stage 6 (Placement) / Stage 7 (Gesture)
# Bright stems move forward/up, dark stems recede

def spectral_driven_placement(profile, mir_summary, stem_id):
    """
    Stems with high spectral contrast → forward placement
    Stems with low spectral contrast → rear placement

    Apply to base_distance (0.52–0.88) dynamically
    """
    spectral_contrast = mir_summary["stems"][stem_id]["features"]["spectral_contrast_mean"]
    # Normalize to [0, 1], apply to distance scaling
```

**Impact:** Natural frequency-based layering without post-processing  
**User Benefit:** Better clarity and separation

---

### Priority 2: Context-Aware Profile Selection (High Impact, Medium Effort)

**Current State:** Fixed profiles per (category, role) regardless of production context

**Proposed Enhancements:**

#### 2.1 Genre-Adaptive Profiles

```python
# New metadata input during Stage 0 (Session)

genre_profiles = {
    "orchestral": {
        "vocals": {"profile": "vocals/lead", "spread": 0.12, "motion": "gentle_drift"},
        "strings": {"profile": "strings/orchestral_ambience", "spread": 0.35, "motion": "orbit"},
        "brass": {"spread": 0.25},  # Wider ensemble blend
    },
    "jazz": {
        "vocals": {"spread": 0.10, "motion": "static_or_drift"},  # Intimate
        "drums": {"spread": 0.15},  # Tighter kit
        "guitar": {"motion": "gentle_drift", "reactivity": "low"},  # Smooth
    },
    "edm": {
        "bass": {"distance": 0.55, "motion": "static"},  # Heavy, grounded
        "synth": {"spread": 0.40, "motion": "orbit"},  # Wide, evolving
        "drums": {"motion": "reactive", "reactivity_scale": 1.5},  # Punchy
    },
}
```

**Impact:** Culturally/stylistically appropriate spatial mixing  
**User Benefit:** Mix recommendations based on genre conventions

#### 2.2 Density-Aware Mixing

```python
# Count active stems at each time frame

def adaptive_profile_by_density(stem_count, baseline_profile):
    """
    Sparse mix (1-3 stems): wider, more enveloping profiles
    Medium mix (4-8 stems): balanced, mid-field
    Dense mix (9+ stems): tighter, clustered, more contrast needed
    """
    if stem_count <= 3:
        return {**baseline_profile, "spread": 0.35, "distance": 0.80}  # Wide
    elif stem_count <= 8:
        return baseline_profile  # Standard
    else:
        return {**baseline_profile, "spread": 0.15, "distance": 0.65}  # Tight
```

**Impact:** Prevents muddiness in dense mixes, maximizes clarity in sparse ones  
**User Benefit:** Automatic optimization without manual tweaking

#### 2.3 Energy Level Context

```python
# Analyze overall mix energy (bass presence, peak loudness, dynamic range)

def energy_profile_modulation(overall_energy: float, profile):
    """
    Low-energy mix: Enhance reactivity, subtle motion for interest
    High-energy mix: Reduce motion variance, focus on placement clarity
    """
    if overall_energy < 0.4:
        return {**profile, "motion_intensity": 0.8, "motion_type": "gentle_drift"}
    elif overall_energy > 0.8:
        return {**profile, "motion_intensity": 0.2, "motion_type": "static"}
```

**Impact:** Intelligently adapts motion to mix character  
**User Benefit:** More cohesive spatial narrative

---

### Priority 3: Advanced Gesture Generation (High Impact, High Effort)

**Current State:** Simple archetypes (static, drift, orbit, reactive)

**Proposed Enhancements:**

#### 3.1 Tempo-Synced Motion (from v3 Roadmap)

```python
# Stage 7: Use tempo_bpm to sync orbital motion

def tempo_synced_orbit(profile, mir_summary, stem_id, duration):
    """
    Orbit speed = 1 beat per cycle (or user-configurable)

    If tempo_bpm = 120, one orbit = 0.5 seconds
    Prevents motion "clicking" between beats
    """
    tempo = mir_summary["stems"][stem_id]["features"]["tempo_bpm"]
    orbit_period = 60.0 / tempo  # seconds per beat
    # Generate keyframes synchronized to beat grid
```

**Impact:** Professional, musically coherent motion  
**User Benefit:** Spatial motion feels rhythmically intentional

#### 3.2 Onset-Driven Reactivity (from v3 Roadmap)

```python
# Stage 7: Use onset_times for precise transient response

def onset_reactive_bursts(profile, mir_summary, stem_id):
    """
    Detect exact onset timestamps from onset_times array
    Generate jitter keyframes at those exact moments
    Scale by onset_strength for dynamic response
    """
    onset_times = mir_summary["stems"][stem_id]["features"]["onset_times"]
    for onset_t in onset_times:
        # Create jitter keyframe at onset_t
        # Magnitude = onset_strength
```

**Impact:** Precise, musically grounded spatial responsiveness  
**User Benefit:** Motion feels reactive to actual audio transients

#### 3.3 Spectral Content-Driven Motion

```python
# Use spectral characteristics to modulate motion parameters

def spectral_motion_modulation(profile, mir_summary, stem_id):
    """
    High brightness (treble): Faster, tighter motion (more active)
    Low brightness (bass): Slower, wider motion (less active but enveloping)
    High flux (noisy): Chaotic, jittery (granular-like)
    Low flux (tonal): Smooth, predictable orbits
    """
    brightness = mir_summary["stems"][stem_id]["features"]["brightness_mean"]
    flux = mir_summary["stems"][stem_id]["features"]["spectral_flux_mean"]

    # Apply to orbit_speed, jitter_magnitude, etc.
```

**Impact:** Motion character naturally reflects content timbre  
**User Benefit:** More intuitive, less "artificial" motion

---

### Priority 4: Stereo Pair & Multi-Channel Intelligence (Medium Impact, Medium Effort)

**Current State:** Stereo pairs split to L/R mono objects with simple ±azimuth offsets

**Proposed Enhancements:**

#### 4.1 Stereo Image Preservation

```python
# Stage 1: Analyze stereo width before splitting

def analyze_stereo_image(stereo_stem, sr=48000):
    """
    Compute:
    - Mid/Side energy ratio (mono-like vs wide)
    - L/R correlation (coherence)
    - Frequency-dependent width (bass narrow, treble wide)

    Return: width_profile = {bass_width, mid_width, treble_width}
    """
    # Apply to azimuth_spread in Stage 5
    # Preserve narrow bass, wide treble naturally
```

**Impact:** Stereo stems don't collapse to mono; character preserved  
**User Benefit:** Stereo reverb, wide guitars, etc. remain spacious

#### 4.2 Multi-Channel Ensemble Coherence

```python
# For multi-stem categories (e.g., drum kit, string section)
# Keep related stems coherent in space

def ensemble_coherence_group(profile_group, z):
    """
    Drum kit: kick stays center, hats narrow ±30°, toms wider ±60°
    String section: maintain natural orchestral spread (violins L, violas C, cellos R)

    GroupId: enforce azimuth constraints across group members
    """
    # Apply soft constraints in Stage 6 (Placement)
```

**Impact:** Related instruments stay grouped, natural ensemble sound  
**User Benefit:** Orchestral/ensemble recordings sound more authentic

---

### Priority 5: Real-Time Mixing Feedback & UI Enhancements (Medium Impact, Low-Medium Effort)

**Current State:** UI shows static preview, limited parameter insight

**Proposed Enhancements:**

#### 5.1 Interactive Profile Preview

```python
# In ui/app.py: Show spatial plot as u, v sliders change

def interactive_spatial_preview(u: float, v: float):
    """
    Real-time update of:
    - Seed matrix z vector (8 dimensions)
    - Profile spread/distance/elevation changes
    - Keyframe distribution (sparse vs dense)

    Display as:
    - 2D azimuth × elevation scatter plot
    - 3D cube visualization (optional)
    - z-vector radar chart
    """
```

**Impact:** Users see spatial impact immediately without full pipeline run  
**User Benefit:** Faster iteration, intuitive parameter learning

#### 5.2 MIR Sensitivity Inspector

```python
# In ui/app.py (Results tab): Show MIR coupling for each stem

def mir_sensitivity_display(stem_id, profile, mir_summary):
    """
    Show:
    - Energy sensitivity: 0.15
    - Flux sensitivity: 0.20
    - Brightness sensitivity: 0.25
    - Predicted motion magnitude for this mix

    Explain: "This violin will move 0.3x reactive intensity"
    """
```

**Impact:** Users understand _why_ stems move, builds confidence  
**User Benefit:** Transparency in algorithm decisions

#### 5.3 Spatial Heatmap Visualization

```python
# In Results tab: Show where stems are positioned over time

def spatial_heatmap(placements, keyframes, duration):
    """
    2D heatmap: time (x-axis) vs azimuth (y-axis)
    Color intensity: how many stems at that position

    Helps identify:
    - Clustering (too many stems in same quadrant)
    - Dead zones (empty regions)
    - Balance (L/R symmetry)
    """
```

**Impact:** Visual balance check, clustering detection  
**User Benefit:** Mix engineer can spot issues at a glance

---

### Priority 6: Performance & Robustness (Medium Impact, Low Effort)

**Current State:** Stages 0-7 working but room for optimization

**Proposed Enhancements:**

#### 6.1 MIR Caching Strategy

```python
# Cache librosa features to disk (already done, but optimize)

# Improvements:
# 1. Cache versioning: invalidate if audio file changes (hash check)
# 2. Selective recomputation: if only u,v change, skip Stage 2-3
# 3. Incremental caching: add new stems without recalculating old ones
```

**Impact:** Repeated runs 5-10x faster  
**User Benefit:** Iteration speed dramatically improved

#### 6.2 Graceful Degradation

```python
# Handle edge cases better

# Improvements:
# 1. If tempo detection fails: use default 120 bpm
# 2. If pitch_confidence too low: skip harmonic decay modulation
# 3. If stereo analysis unclear: fall back to mono-like spread
# 4. If gesture generation fails: use static fallback
```

**Impact:** No crashes on unusual audio  
**User Benefit:** Robust, production-ready

#### 6.3 Parallel Processing

```python
# Use multiprocessing for independent stages

# Easy parallelization:
# 1. MIR extraction per-stem (Stage 2): 4-6 stems → 4-6x speedup
# 2. Gesture generation per-stem (Stage 7): independent keyframes
# 3. Classification per-stem (Stage 3): independent heuristics

# Would reduce ~30s MIR time to ~8s on 4-core machine
```

**Impact:** 3-4x speedup for heavy workloads  
**User Benefit:** Real-time feedback possible

---

## 📊 Feature Matrix

| Feature                        | Effort | Impact | Priority | Timeline         |
| ------------------------------ | ------ | ------ | -------- | ---------------- |
| **Adaptive MIR-Driven Mixing** | M      | H      | 1        | v2.3 (2-3 weeks) |
| — Energy-adaptive elevation    | M      | M      | 1a       | v2.3             |
| — Spectral-driven placement    | M      | M      | 1b       | v2.3             |
| **Context-Aware Selection**    | M      | H      | 2        | v2.4 (3-4 weeks) |
| — Genre profiles               | M      | H      | 2a       | v2.4             |
| — Density-aware                | M      | M      | 2b       | v2.4             |
| — Energy context               | S      | M      | 2c       | v2.4             |
| **Advanced Gestures**          | H      | H      | 3        | v3.0 (4-6 weeks) |
| — Tempo-synced orbit           | M      | H      | 3a       | v3.0             |
| — Onset-reactive               | M      | H      | 3b       | v3.0             |
| — Spectral motion              | M      | M      | 3c       | v3.0             |
| **Stereo Intelligence**        | M      | M      | 4        | v2.5 (2-3 weeks) |
| **UI Enhancements**            | L-M    | M      | 5        | v2.3-2.4         |
| — Interactive preview          | L      | M      | 5a       | v2.3             |
| — MIR inspector                | L      | M      | 5b       | v2.3             |
| — Spatial heatmap              | M      | M      | 5c       | v2.4             |
| **Performance**                | L      | M      | 6        | v2.3 (ongoing)   |
| — Caching strategy             | L      | H      | 6a       | v2.3             |
| — Graceful degradation         | S      | H      | 6b       | v2.3             |
| — Parallel processing          | M      | H      | 6c       | v2.5             |

---

## 🔄 Recommended Implementation Order

### **Phase 1: Quick Wins (v2.3 — 2-3 weeks)**

Focus on low-effort, high-impact items and foundation for future work.

1. **6a. MIR Caching** — 1-2 days
   - Hash-based invalidation
   - Selective recomputation
   - 5-10x speedup on re-runs

2. **6b. Graceful Degradation** — 1-2 days
   - Fallback mechanisms for edge cases
   - Robustness improvements

3. **5a. Interactive Spatial Preview** — 3-4 days
   - Real-time u,v → z visualization
   - Builds UI foundation

4. **5b. MIR Sensitivity Inspector** — 2-3 days
   - Show coupling values per stem
   - Explain motion drivers

5. **1.2 Energy-Adaptive Elevation** — 2-3 days
   - Gentle elevation modulation
   - Immediate perceptual improvement

### **Phase 2: Core Enhancements (v2.4 — 3-4 weeks)**

Build on Phase 1 foundation, add context awareness.

1. **2a. Genre-Adaptive Profiles** — 5-7 days
   - Define profile overrides per genre
   - UI genre selector
   - Test with diverse music

2. **2b. Density-Aware Mixing** — 3-4 days
   - Automatic spread/distance scaling
   - Test with sparse & dense mixes

3. **1.3 Spectral-Driven Placement** — 3-4 days
   - Brightness → forward/backward
   - Integrate with Stage 6

4. **5c. Spatial Heatmap** — 4-5 days
   - Time × azimuth visualization
   - Clustering detection

5. **4.1 Stereo Image Preservation** — 4-5 days
   - Mid/Side analysis pre-split
   - Width-adaptive profiles

### **Phase 3: Advanced Features (v3.0 — 4-6 weeks)**

Long-term, high-impact gesture generation improvements.

1. **3a. Tempo-Synced Orbit** — 4-5 days
   - Tempo extraction (existing)
   - Beat-grid synchronization
   - Keyframe timing

2. **3b. Onset-Reactive Bursts** — 4-5 days
   - Onset detection (existing)
   - Precise timing + magnitude
   - Test with drums/percussion

3. **3c. Spectral Motion Modulation** — 3-4 days
   - Brightness ↔ motion speed
   - Flux ↔ motion character

4. **6c. Parallel Processing** — 5-7 days
   - Multiprocessing pool for Stages 2, 3, 7
   - Benchmark improvements

5. **4.2 Ensemble Coherence** — 5-7 days
   - GroupId constraints
   - Orchestral/ensemble testing

---

## 🎯 User-Facing Improvements By Version

### v2.3 (Quick Wins)

- **UI:** Interactive spatial preview, MIR sensitivity inspector
- **Performance:** 5-10x faster re-runs (caching)
- **Quality:** Energy-adaptive elevation, better error handling
- **Message:** "Faster iteration, instant feedback, more intelligent mixing"

### v2.4 (Context Awareness)

- **UI:** Genre selector, spatial heatmap
- **Quality:** Genre-appropriate profiles, density-aware mixing, stereo preservation
- **Message:** "Genre-aware mixing, automatic optimization for any session size"

### v3.0 (Advanced Gestures)

- **Quality:** Tempo-synced motion, onset-driven reactivity, spectral-aware movement
- **Performance:** 3-4x faster with parallel processing
- **Message:** "Professional-grade spatial mixing with beat-aware motion"

---

## 📝 Documentation To Create/Update

- [ ] `ENHANCEMENT_ROADMAP.md` (this file + version)
- [ ] `MIR_ADVANCED_FEATURES.md` (energy-adaptive, spectral-driven)
- [ ] `GESTURE_V3_DETAILED.md` (tempo-sync, onset-reactive implementation)
- [ ] `STEREO_PRESERVATION.md` (mid/side analysis, width profiles)
- [ ] `GENRE_PROFILES.md` (orchestral, jazz, EDM, pop, etc.)
- [ ] `UI_ROADMAP.md` (interactive preview, heatmap, inspector)

---

## 🚀 Next Immediate Step

**Recommendation:** Start with **Phase 1 (v2.3)** — Quick Wins

**First Task:** Implement MIR Caching (6a) + Graceful Degradation (6b)

- Foundation for all future iterations
- Immediate user benefit (speed)
- Low risk, high confidence

**Timeline:** 2-3 days, ready for v2.3 release

Would you like me to:

1. Prioritize a specific feature from Phase 1?
2. Deep-dive into implementation details for any priority?
3. Create detailed specifications for the first feature?
4. Set up code scaffolding for Phase 1?

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-29  
**Status:** Ready for implementation planning
