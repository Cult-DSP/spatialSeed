# Export Architecture

SpatialSeed provides two explicit export paths:

## 1. Export LUSID Package
This is the canonical spatial scene format. It produces a directory containing:
- `scene.lusid.json`: The spatial metadata and keyframes.
- `containsAudio.json`: Channel mapping and RMS levels.
- `mir_summary.json`: A summary of extracted MIR features.
- `*.wav`: Mono 48kHz audio files for beds, LFE, and all objects.

## 2. Export ADM BWF (via CULT Transcoder)
This provides compatibility with DAWs like Logic Pro. 
- It relies completely on the external `cult-transcoder` submodule.
- SpatialSeed does **not** implement Python-based ADM authoring. 
- The pipeline invokes `cult_transcoder/build/cult-transcoder adm-author` as a subprocess.
- It takes the generated LUSID Package as input and outputs `export.adm.wav` and `export.adm.xml`.

If CULT Transcoder is not built or fails, SpatialSeed surfaces the error to the user.
