# SpatialSeed MIR Pipeline

The SpatialSeed MIR (Music Information Retrieval) pipeline is responsible for analyzing audio stems, extracting acoustic features, and automatically classifying them by instrument category and musical role.

The pipeline is explicitly split into two stages to ensure speed, stability, and graceful degradation:

1. **Stage 2: MIR Extraction** (`src/mir/extract.py`)
2. **Stage 3: Classification & Role Assignment** (`src/mir/classify.py`)

---

## 1. Extraction (`src/mir/extract.py`)

This stage performs deep signal analysis to extract summary statistics for each stem and the stereo mix.

### Core Design

- **Library**: Relies entirely on `librosa` (pure Python/NumPy, ISC licensed).
- **Performance**: Audio processing is parallelized across CPU cores using `ProcessPoolExecutor`.
- **Caching**: Computations are heavy, so results are cached locally in `cache/mir/` using the audio file's hash as the cache key.
- **Output**: Writes a flat dictionary of scalar summary features per stem to `mir_summary.json`.

### Extracted Features

- **Loudness & Dynamics**: RMS energy (`rms_energy`), Zero Crossing Rate (`zero_crossing_rate_mean`).
- **Timbre**: Spectral centroid (`spectral_centroid_mean`, `_std`), Spectral flatness (`spectral_flatness_mean`), MFCCs (`mfcc_mean`), Spectral contrast (`spectral_contrast_mean`).
- **Rhythm & Transients**: Spectral flux (`spectral_flux_mean`), Onset density (`onset_density`), Max onset strength (`max_onset_strength`), Tempo (`tempo_bpm`). Backtracking is used to align onsets with transient beginnings.
- **Pitch & Harmonics**: Pitch confidence (`pitch_confidence_mean`), Harmonic-percussive ratio (`harmonic_ratio`), Tonnetz tonal centroids (`tonnetz_mean`).
- **Stereo Mix Features**: Analyzes the reference mix for stereo width, L/R energy balance, and L/R Pearson correlation.

---

## 2. Classification & Role Assignment (`src/mir/classify.py`)

This stage consumes the `mir_summary.json` outputs and assigns contextual metadata to the stems to inform spatial placement rules later in the pipeline.

### Output Taxonomies

- **Categories**: `vocals`, `bass`, `drums`, `percussion`, `guitar`, `keys`, `pads`, `fx`, `other`, `unknown`.
- **Roles**: `bass`, `rhythm`, `lead`, `percussion`, `fx`, `unknown`.

### Graceful Fallback Strategy

Classification uses a multi-tier fallback approach. If a high-tier strategy fails or is uncertain, it falls through to the next deterministic tier.

#### Tier 1: Machine Learning (Essentia)

- **Library**: `essentia-tensorflow` (AGPLv3 licensed). Loaded _lazily_ to prevent crashing environments where TensorFlow cannot be installed.
- **Instrument Model**: `mtg_jamendo_instrument-discogs-effnet` (Maps 40 multi-label classes to our 10 canonical categories). Requires a `0.35` probability threshold and a `0.05` margin over the runner-up.
- **Role Model**: `fs_loop_ds-msd-musicnn` (5 loop classes mapped to our 6 canonical roles). Requires a `0.60` probability threshold.

#### Tier 2: Filename Heuristics

If Essentia is unavailable or uncertain, deterministic regex matching is applied to the filename (e.g., matching `"vox"`, `"LV"`, `"BV"` -> Category: `vocals`, Role: `lead`).

#### Tier 3: MIR Feature Heuristics

If the filename offers no clues, the deterministic `librosa` features from Stage 2 are evaluated against tuned thresholds.

- _Example_: If `max_onset_strength > 10.0`, `pitch_conf < 0.3`, and `harmonic_ratio < 0.4`, it's classified as `drums`.
- _Example_: If `pitch_conf > 0.75` and `1000 < centroid < 4000`, along with specific mid-band spectral contrasts, it's classified as `vocals`.

---

## Architectural Decisions

### Separation of Licenses & Dependencies

By strictly confining `essentia-tensorflow` (heavy dependency, strict AGPLv3 copyleft license) to the classification tier and importing it lazily, the rest of the project can remain lightweight and permissively licensed. If the user doesn't have Essentia installed, the system gracefully falls back to the deeply extracted `librosa` features to categorize stems deterministically.

### Determinism and Override

All `mir_summary.json` and classification results are cached by file hash. Because fallbacks use mathematical thresholds and regex, they guarantee reproducible results across runs if ML models are skipped. Future updates allow users to manually override these automated classifications in the UI before spatial generation occurs.

---

## 3. Downstream Consumption (Spatial Mapping)

The MIR data extracted and classified in Stages 2 and 3 is consumed by the spatial processing pipeline to inform intelligent placement and movement.

### SPF Resolution (`src/spf.py`)

The assigned **Category** and **Role** act as keys to resolve the stem's `InstrumentProfile`.

- _Example:_ A stem classified as `vocals` + `lead` gets a profile anchoring it front-center with a tight spread, whereas `pads` + `rhythm` gets a profile with wide panning and high elevation to envelope the listener.

### Gesture Generation (`src/gesture_engine.py`)

The quantitative features from Stage 2 are used directly to drive dynamic spatial motion:

- **Onset Density:** Drives the frequency and intensity of "reactive" motion bursts. A highly percussive stem with a high onset density will generate more spatial keyframes, jittering or expanding synchronously with its transients.
- **Future Extensions:** Currently, onset density drives reactive jitter. The pipeline is designed so that the newly added features (like `tempo_bpm` or `spectral_contrast`) can be mapped directly to orbital speeds, sweeping motions, or parameter modulations in the LUSID scene.
