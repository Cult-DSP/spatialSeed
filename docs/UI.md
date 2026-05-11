# User Interface (Streamlit)

The SpatialSeed UI (`ui/app.py`) is designed as a professional audio-tool dashboard, aligning with the **Spatial Root UI** aesthetic.

## Visual Design Language
- **Dark Theme:** Deep near-black background (`#0f0f0f`) for the application shell.
- **Parchment Panels:** Warm off-white (`#f5f2e9`) control panels for high contrast and a premium hardware feel.
- **Technical Typography:** Monospaced JetBrains Mono/Source Code Pro font stack for all technical data and controls.
- **Utilitarian Layout:** Dense but readable organization with subtle borders and minimal decorative styling.
- **Status Visibility:** A dedicated header status indicator tracking the pipeline lifecycle.

## Workflow Organization (Tabs)

### 1. AUTHOR
- **Input Configuration:** Configure base output directory, session name, and stems source folder.
- **Discover Stems:** Scan and validate input audio files.
- **Seed Matrix Controls:** Slider-based `u`/`v` selection with an interactive 2D canvas visualization.

### 2. ANALYZE
- **Classification / Stems:** Review detected stems and their MIR-driven classifications.
- **Overrides:** Manually override instrument category and role assignments per node.

### 3. EXPORT
- **Export Controls:** Trigger the full LUSID package generation.
- **ADM BWF Integration:** Optional toggle to invoke the `cult-transcoder` bridge for DAW-compatible export.
- **Export Status:** Direct feedback on generated package paths and file counts.

### 4. RESULTS
- **Spatial Summary:** High-level metrics on objects, keyframes, and motion types.
- **Style Vector (z):** Breakdown of the 8-dimensional style vector derived from the Seed Matrix.
- **Placement Summary:** Detailed list of XYZ Cartesian coordinates for all spatial objects.

### 5. LOGS
- **Pipeline Log:** Real-time capture of stdout/stderr from the underlying Python pipeline for debugging and audit.

## Status Indicator Meanings
- `IDLE`: Initial state, awaiting configuration.
- `READY`: Stems have been discovered and validated.
- `RUNNING`: Pipeline stages are currently executing.
- `ERROR`: A failure occurred during discovery or generation (see LOGS).
- `EXPORTED`: Generation complete and assets are ready at the output path.

## Implementation Details
- **Streamlit Native:** Uses Streamlit columns, containers, and tabs for structure.
- **Custom CSS:** Injected CSS for deep styling of backgrounds, cards, buttons, and typography.
- **Altair Visualization:** Seed Matrix view rendered via declarative Altair charts.
- **Zero-Dependency UI:** Avoids complex frontend frameworks, relying on standard Streamlit capabilities and clean CSS.
