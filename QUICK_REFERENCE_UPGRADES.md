# Quick Reference: Essentia Removal & Upgrades (TL;DR)

## 1. Remove Essentia in 5 Steps

**Why?** AGPLv3 license, heavy deps (TensorFlow), only used as optional Tier-1 classifier.

**Files to touch:**

| File                  | Action                                 |
| --------------------- | -------------------------------------- |
| `src/mir/classify.py` | Delete Essentia import + model loading |
| `requirements.txt`    | Delete essentia-tensorflow + essentia  |
| `init.sh`             | Delete Essentia model download section |
| `agents.md`           | Update Section 13.1 → 13.2 (MIR-only)  |
| `README.md`           | Remove Essentia from Dependencies      |

**Expected outcome:** Fallback chain collapses to:

1. Filename regex (e.g., `"vox"` → vocals)
2. MIR heuristics (e.g., high pitch_conf → vocals)

**Test:** `pytest tests/test_stages_0_3.py -v` (should still pass)

---

## 2. Upgrade Seed Matrix (Choose One)

**Current:** Linear mapping `(u,v) → z = [z₁, z₂, ..., z₈]`

**Problems:**

- No curvature (purely linear)
- Ensemble cohesion always 0.5
- MIR coupling computed but unused

### Option A: Smooth Nonlinear (Recommended for v2)

Replace in `src/seed_matrix.py`:

```python
def seed_matrix_mapping(u: float, v: float) -> np.ndarray:
    # Use smooth curves (Hermite, sigmoid)
    # Add interaction terms (u*v, powers)
    # Make z[6] (ensemble_cohesion) active: (1-v) * (0.8 + 0.2*(1-u))
    # Make z[7] (mir_coupling) stronger: (u*v)^0.8
```

**Implementation time:** 2 hours  
**Complexity:** Medium  
**Backward compat:** Mostly (new z values, existing playgrounds may need re-tuning)

### Option B: Data-Driven (Post-Release)

Train a polynomial regressor on user feedback:

```python
# After collecting real user sessions, fit z = f(u,v)
from sklearn.preprocessing import PolynomialFeatures
poly = PolynomialFeatures(degree=3)
# ...fit on user data...
```

**Implementation time:** 4 hours (assumes user data exists)  
**Complexity:** Medium  
**Backward compat:** No (entirely new mapping)

### Option C: Analytical Rationale (Document-first)

Define spatial audio design principles in prose, then implement:

```
u=0 (Conservative): tight, symmetric, front-heavy, low complexity
u=1 (Experimental): wide, asymmetric, varied, high complexity
v=0 (Static): no motion, ground-level, no reactivity
v=1 (Immersive): orbits, full height, reactive to onsets
```

**Implementation time:** 3 hours  
**Complexity:** Low  
**Backward compat:** Partial (rationale-driven, may differ from current)

**Files to touch:**

| File                              | Change                                   |
| --------------------------------- | ---------------------------------------- |
| `src/seed_matrix.py`              | Replace mapping function + add docstring |
| `tests/test_seed_matrix.py`       | Update expected z values                 |
| `internalDocs/lowLevelSpecsV1.md` | Add "v2 design principles" section       |

**Test:**

```bash
pytest tests/test_seed_matrix.py -v
pytest tests/test_stages_0_9.py -v  # full pipeline
```

---

## 3. Upgrade SPF (Choose One)

**Current:** 10 category/role profiles (limited coverage)

**Problems:**

- Missing percussion, choir, orchestral variants
- No context awareness (genre, energy)
- Gesture engine doesn't use all profile parameters

### Option A: Expand Coverage (Recommended for v2)

Add 10–20 new profiles in `src/spf.py`:

```python
PROFILES = {
    # Existing 10
    "vocals/lead": ...,
    ...
    # NEW: Percussion variants
    "percussion/melodic": ...,
    "percussion/mallet": ...,
    # NEW: Vocal variants
    "vocals/harmony": ...,
    "vocals/ambient": ...,
    # NEW: Strings / Brass / Woodwinds / Synth
    "strings/lead": ...,
    "brass/lead": ...,
    "woodwinds/lead": ...,
    "synth/pad": ...,
}
```

**Implementation time:** 3 hours  
**Complexity:** Low  
**Backward compat:** Yes (new categories only)

**Files to touch:**

| File                              | Change                           |
| --------------------------------- | -------------------------------- |
| `src/spf.py`                      | Expand `init_default_profiles()` |
| `internalDocs/lowLevelSpecsV1.md` | Add profile reference table      |

**Test:**

```bash
pytest tests/test_stages_0_9.py -v
```

### Option B: Context-Aware Selection (v3+)

Allow profiles to vary by genre, tempo, energy:

```python
def resolve_style_profile_contextual(
    category, role, z, mir, metadata=None
):
    # Select profile based on genre, bpm, energy
    # Modulate based on context (e.g., jazz guitar ≠ rock guitar)
```

**Implementation time:** 4 hours  
**Complexity:** Medium  
**Backward compat:** No (new API)

### Option C: Parametric Gesture System (v3+)

Upgrade gesture_engine to use tempo_bpm, onsets, spectral features:

```python
class MotionArchetype:
    def generate_keyframes(self, ..., mir_summary, intensity):
        # Use mir_summary.tempo_bpm for orbit sync
        # Use mir_summary.onset_times for reactive bursts
        # Use profile.orbit_radius, orbit_speed for modulation
```

**Implementation time:** 6 hours  
**Complexity:** High  
**Backward compat:** Partial (existing gestures still work, but enhanced)

---

## 4. Implementation Priority

**Recommended order (v2 roadmap):**

1. **Remove Essentia** (1–2 hours) → Test → Commit
2. **Upgrade Seed Matrix** (Option A, 2 hours) → Test → Commit
3. **Expand SPF profiles** (Option A, 3 hours) → Test → Commit

**Total for all three:** ~6–7 hours, 3 separate PRs, each tested independently.

---

## 5. Testing Checklist

After each change:

```bash
source activate.sh

# Test classification (Essentia removal)
pytest tests/test_stages_0_3.py -v

# Test Seed Matrix
pytest tests/test_seed_matrix.py -v

# Test full pipeline
pytest tests/test_stages_0_9.py -v

# Expected: ✅ All pass
```

---

## 6. Files to Read Before Starting

| File                              | Section/Purpose                           |
| --------------------------------- | ----------------------------------------- |
| `internalDocs/agents.md`          | Section 2 (non-negotiables), Section 13.1 |
| `internalDocs/lowLevelSpecsV1.md` | Seed Matrix design, SPF profiles          |
| `internalDocs/MIR.md`             | MIR extraction + classification arch      |
| `src/seed_matrix.py`              | Current implementation                    |
| `src/spf.py`                      | Current profiles + resolver               |
| `src/mir/classify.py`             | Essentia usage (Tier 1 fallback)          |

---

## 7. Rollback Plan

If something breaks:

```bash
# Revert last commit
git revert HEAD

# Re-run tests
pytest tests/test_stages_0_9.py -v

# Check git log
git log --oneline -5
```

All three upgrades are independent; one failure doesn't break the others.

---

## 8. One-Liner Summary

| Task                | What to Do                                  | Time   | Priority |
| ------------------- | ------------------------------------------- | ------ | -------- |
| Remove Essentia     | Delete import + pip deps, keep fallbacks    | 1–2 hr | High     |
| Upgrade Seed Matrix | Add smooth curves + interactions to (u,v)→z | 2 hr   | Medium   |
| Expand SPF          | Add 10–20 new category/role profiles        | 3 hr   | Medium   |

---

## Questions?

See the full guide: `ONBOARDING_ESSENTIA_UPGRADE.md`
