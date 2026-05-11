# MIR & Classification Pipeline

The MIR (Music Information Retrieval) pipeline is the "brain" of SpatialSeed, enabling automated spatial decisions based on the content of the audio.

## 1. Feature Extraction (`src/mir/extract.py`)
Extracts summary statistics for each stem using `librosa`.

### Analyzed Features
- **Loudness:** `rms_energy` (dB).
- **Timbre:** Spectral Centroid (brightness), Spectral Flatness, MFCCs, Spectral Contrast.
- **Rhythm:** Spectral Flux, Onset Density, Tempo (BPM).
- **Pitch:** Pitch Confidence, Harmonic-Percussive Ratio, Tonnetz (tonality).

## 2. Instrument Classification (`src/mir/classify.py`)
Assigns a `category` and `role_hint` to each stem.

### Taxonomy
- **Categories:** `vocals`, `bass`, `drums`, `percussion`, `guitar`, `keys`, `pads`, `fx`, `other`, `unknown`.
- **Roles:** `bass`, `rhythm`, `lead`, `percussion`, `fx`, `unknown`.

### Multi-Tier Classification Logic
SpatialSeed uses a tiered approach to ensure a result is always found:

#### Tier 1: Machine Learning (Essentia)
- **Library:** `essentia-tensorflow`.
- **Logic:** Uses EffNet-Discogs for instruments and MusiCNN for loops. 
- **Requirement:** Probability must exceed `0.35` with a `0.05` margin over the runner-up.

#### Tier 2: Filename Heuristics
- **Logic:** Regex matching against the stem filename.
- **Examples:**
  - `*vox*`, `*LV*`, `*BV*` → `vocals`
  - `*kick*`, `*snare*`, `*hat*` → `drums`
  - `*synth*`, `*rhodes*` → `keys`

#### Tier 3: MIR Heuristics
- **Logic:** Rule-based thresholds on signal features.
- **Examples:**
  - High `onset_strength` + low `pitch_conf` → `drums`
  - High `pitch_conf` + mid-range `centroid` → `vocals`
  - Low `centroid` + low `zero_crossing_rate` → `bass`

## 3. User Overrides
Classifications can be manually overridden in the Streamlit UI. Overrides are injected into the pipeline at Stage 3, bypassing the automated logic for specified Node IDs.
