# User Interface (Streamlit)

The SpatialSeed UI (`ui/app.py`) is designed as a modern, clean authoring dashboard.

## Design Direction
- **Minimalist Aesthetic:** Focuses on the Seed Matrix and spatial data, using custom CSS to match the brand identity.
- **Clear Workflows:** Guides the user through a linear process: 
  1. Set Project/Stems paths.
  2. Discover Stems.
  3. Optionally override classifications.
  4. Generate Scene.
  5. Export LUSID or ADM BWF.
- **Visibility:** Provides a summary of generated keyframes, clamped positions, classification overrides, and export status.

## UI Components
- **Sidebar:** For project setup and `u`/`v` slider controls.
- **Matrix View:** A 2D Altair scatter plot visualizing the current `u`/`v` selection.
- **Stems Tab:** Allows granular inspection of discovered stems and manual override of assigned instrument roles.
- **Results Tab:** Displays output statistics, pipeline logs, export paths, and spatial previews.
