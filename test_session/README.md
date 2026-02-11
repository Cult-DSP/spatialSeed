# Test Session

Place your input stems in the `stems/` folder, then run the pipeline:

```bash
source activate.sh
python src/pipeline.py test_session/stems --project-dir test_session -u 0.5 -v 0.3
```

## Expected stem files

Drop WAV files (any sample rate -- they will be resampled to 48 kHz) into `stems/`.
Mono and stereo files are both supported. Stereo stems are split into two objects (L/R).

Naming tips for best classification results (filename fallback heuristics):

- Include `vox` or `vocal` for vocal stems
- Include `bass` for bass stems
- Include `drum`, `kick`, `snare`, `hat`, or `perc` for drums/percussion
- Include `gtr` or `guitar` for guitar stems
- Include `keys`, `piano`, `rhodes`, `organ`, `synth`, or `pad` for keys/pads

Examples:

```
stems/
  vocal_lead.wav
  bass_synth.wav
  drums_kit.wav
  guitar_rhythm.wav
  pad_ambient.wav
```

## Outputs

After running the pipeline, outputs will appear in:

- `test_session/manifest.json` -- session manifest
- `test_session/work/` -- intermediate files (normalised WAVs, MIR data)
- `test_session/export/` -- final LUSID package and optional ADM/BW64
