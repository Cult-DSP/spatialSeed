#!/usr/bin/env python3
"""
Generate synthetic test stems for SpatialSeed pipeline testing.

Creates short WAV files with identifiable spectral characteristics:
  - vocal_lead.wav    : sine sweep  ~300-3000 Hz  (mono, 44100 Hz)
  - bass_synth.wav    : low sine    ~80 Hz        (mono, 44100 Hz)
  - drums_loop.wav    : noise bursts               (mono, 44100 Hz)
  - guitar_rhythm.wav : mid-range sine             (stereo, 44100 Hz)

Run:
    python tests/generate_test_stems.py
"""

import numpy as np
import soundfile as sf
from pathlib import Path

DURATION = 5.0          # seconds
SR = 44100              # intentionally NOT 48 kHz -- pipeline must resample
OUTPUT_DIR = Path(__file__).resolve().parent / "test_stems"


def _fade(y: np.ndarray, fade_samples: int = 256) -> np.ndarray:
    """Apply short fade-in / fade-out to avoid clicks."""
    y = y.copy()
    fade = np.linspace(0, 1, fade_samples, dtype=np.float32)
    y[:fade_samples] *= fade
    y[-fade_samples:] *= fade[::-1]
    return y


def make_vocal(sr: int, dur: float) -> np.ndarray:
    """Sine sweep 300-3000 Hz -- mimics tonal vocal content."""
    t = np.linspace(0, dur, int(sr * dur), dtype=np.float32)
    freq = 300 + 2700 * (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    y = 0.5 * np.sin(phase).astype(np.float32)
    return _fade(y)


def make_bass(sr: int, dur: float) -> np.ndarray:
    """Low sine at 80 Hz -- should classify as bass via MIR heuristics."""
    t = np.linspace(0, dur, int(sr * dur), dtype=np.float32)
    y = 0.6 * np.sin(2 * np.pi * 80 * t).astype(np.float32)
    return _fade(y)


def make_drums(sr: int, dur: float) -> np.ndarray:
    """Periodic noise bursts -- high onset density, low pitch confidence."""
    n_samples = int(sr * dur)
    y = np.zeros(n_samples, dtype=np.float32)
    rng = np.random.default_rng(42)
    burst_len = int(sr * 0.03)  # 30 ms bursts
    interval = int(sr * 0.15)   # ~6.7 onsets/sec
    for start in range(0, n_samples - burst_len, interval):
        y[start : start + burst_len] = rng.uniform(-0.7, 0.7, burst_len).astype(
            np.float32
        )
    return _fade(y)


def make_guitar_stereo(sr: int, dur: float) -> np.ndarray:
    """Mid-range harmonic sine (stereo) -- tests stereo split path."""
    t = np.linspace(0, dur, int(sr * dur), dtype=np.float32)
    fundamental = 330.0  # E4
    left = 0.4 * np.sin(2 * np.pi * fundamental * t).astype(np.float32)
    # Right channel slightly detuned for width
    right = 0.4 * np.sin(2 * np.pi * (fundamental + 1.5) * t).astype(np.float32)
    stereo = np.stack([_fade(left), _fade(right)], axis=-1)  # (samples, 2)
    return stereo


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating test stems in {OUTPUT_DIR}")

    specs = [
        ("vocal_lead.wav", make_vocal(SR, DURATION)),
        ("bass_synth.wav", make_bass(SR, DURATION)),
        ("drums_loop.wav", make_drums(SR, DURATION)),
        ("guitar_rhythm.wav", make_guitar_stereo(SR, DURATION)),
    ]

    for name, audio in specs:
        path = OUTPUT_DIR / name
        sf.write(str(path), audio, SR, subtype="FLOAT")
        if audio.ndim == 1:
            ch_label = "mono"
        else:
            ch_label = f"{audio.shape[1]}ch"
        print(f"  {name:25s}  {ch_label}  {SR} Hz  {DURATION:.1f}s")

    print("Done.")


if __name__ == "__main__":
    main()
