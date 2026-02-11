# spatialseed/mir/classify — v1 implementation spec
**Date:** 2026-02-10

## Goal
Given a mono stem WAV (48 kHz project rate), output:
- canonical `category` (vocals, bass, drums, guitar, keys, pads, other, unknown)
- `role_hint` (bass, rhythm/harmony, lead, percussion/drums, fx/ambience, unknown)
- confidences + top raw labels
- deterministic fallbacks

## Default backend (v1)
### Instrument category
- Essentia model: `mtg_jamendo_instrument-discogs-effnet` (multi-label)

### Role hint
- Essentia model: `fs_loop_ds-msd-musicnn` (single-label)

## API
```python
def classify_node(wav_path: str, node_id: str, stem_name: str | None = None) -> dict:
    return {
        "node_id": node_id,
        "category": "vocals|bass|drums|guitar|keys|pads|other|unknown",
        "category_confidence": 0.0,
        "role_hint": "bass|rhythm|lead|percussion|fx|unknown",
        "role_confidence": 0.0,
        "top_labels": [{"label": "voice", "p": 0.91}, ...],
        "backend": {
            "instrument_model": "mtg_jamendo_instrument-discogs-effnet-?.pb",
            "embedding_model": "discogs-effnet-bs64-?.pb",
            "role_model": "fs_loop_ds-msd-musicnn-?.pb",
            "role_embedding_model": "msd-musicnn-?.pb",
        },
        "fallbacks_used": ["filename|mir|none"]
    }
```

## Thresholds (initial defaults)
- instrument category accept if `score >= 0.35` and margin >= 0.05
- role accept if `max(prob) >= 0.60`

## Caching
- `cache/classify/<audio_hash>.json`
- optional: embeddings cache

## Notes
- Resample internally to 16 kHz for Essentia TF model inference.
- Keep backends swappable: future commercial-ready option may use YAMNet or OpenL3+prototypes.
