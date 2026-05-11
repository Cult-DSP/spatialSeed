# Workflows

SpatialSeed supports both CLI and GUI workflows. Both expose identical core functionality and utilize the same `SpatialSeedPipeline`.

## CLI Workflow
Ideal for batch processing or CI/CD testing.
```bash
# Basic run
python -m src.pipeline test_session/stems/ --project-dir test_session/ -u 0.5 -v 0.3

# Run with ADM BWF export
python -m src.pipeline test_session/stems/ --project-dir test_session/ -u 0.5 -v 0.3 --export-adm
```

## GUI Workflow
Ideal for interactive authoring, manual override tuning, and visual feedback.
```bash
streamlit run ui/app.py
```
1. Enter your `Project Directory` and `Stems Directory` in the sidebar.
2. Click **Discover Stems**.
3. Adjust the `u` and `v` parameters.
4. Click **Generate Scene**.
5. Once generated, explicitly click the export buttons for **LUSID Package** or **ADM BWF**.
