# Validation & Testing

SpatialSeed emphasizes correctness and reproducible builds.

## Smoke Testing
Run the comprehensive smoke test to validate stages 0 through 10 (LUSID + ADM Export).
```bash
python tests/test_stages_0_9.py
```
*Note: Ensure you have compiled `cult_transcoder` first.*

## What is Validated
- **Determinism:** Identical input stems and `u`/`v` settings must produce identical object IDs, file names, and keyframes.
- **Coordinate Clamping:** All generated XYZ coordinates are asserted to fall within `[-1, 1]`.
- **Package Integrity:** `containsAudio.json` must exactly match the number of output WAVs.
- **ADM Export:** Verifies that CULT Transcoder runs successfully and produces the expected interleaved `.wav` and `.xml` sidecar.

## Manual Testing (GUI)
1. Run `streamlit run ui/app.py`.
2. Discover stems using the `test_session/stems/` directory.
3. Click "Generate Scene".
4. Use the "Export ADM" button and verify success.
