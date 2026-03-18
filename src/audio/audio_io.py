"""
SpatialSeed Audio I/O and Normalization
========================================
Stage 1: Normalize + Split Audio

Responsibilities:
- Resample all audio to 48 kHz (project rate)
- Split stereo stems to two mono buffers
- Create silent bed WAVs (1.1 through 10.1, excluding 4.1)
- Create silent LFE.wav
- Write normalized mono WAVs for all objects

Per spec: lowLevelSpecsV1.md 7, agents.md 2.1, 2.4
"""

import logging
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import soundfile as sf
import librosa

logger = logging.getLogger("spatialSeed.audio_io")


class AudioNormalizer:
    """
    Handles audio resampling, stereo splitting, and WAV generation.

    Per spec (agents.md 2.1):
    - Target: 48 kHz, float32, mono
    - NO gain changes (no LUFS/peak normalization in v1)
    """

    TARGET_SAMPLE_RATE = 48000
    SAMPLE_FORMAT = np.float32  # v1: float32

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize audio normalizer.

        Args:
            cache_dir: Optional directory for caching processed audio
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Resampling
    # ------------------------------------------------------------------

    def resample_to_48k(self, audio: np.ndarray, original_sr: int) -> np.ndarray:
        """
        Resample audio to 48 kHz using librosa (high-quality kaiser_best).

        Args:
            audio: Input audio array. Shape (samples,) for mono or
                   (channels, samples) for multi-channel.
            original_sr: Original sample rate

        Returns:
            Resampled audio at 48 kHz, same shape convention.

        Per spec (agents.md 2.1):
        - Resample only, NO gain changes
        """
        if original_sr == self.TARGET_SAMPLE_RATE:
            return audio.astype(self.SAMPLE_FORMAT)

        logger.info(
            "Resampling from %d Hz to %d Hz", original_sr, self.TARGET_SAMPLE_RATE
        )

        if audio.ndim == 1:
            # Mono
            resampled = librosa.resample(
                audio.astype(np.float32),
                orig_sr=original_sr,
                target_sr=self.TARGET_SAMPLE_RATE,
            )
        elif audio.ndim == 2:
            # Multi-channel: resample each channel independently
            channels = []
            for ch in range(audio.shape[0]):
                channels.append(
                    librosa.resample(
                        audio[ch].astype(np.float32),
                        orig_sr=original_sr,
                        target_sr=self.TARGET_SAMPLE_RATE,
                    )
                )
            resampled = np.stack(channels, axis=0)
        else:
            raise ValueError(f"Unsupported audio shape: {audio.shape}")

        return resampled.astype(self.SAMPLE_FORMAT)

    # ------------------------------------------------------------------
    # Stereo splitting
    # ------------------------------------------------------------------

    def split_stereo_to_mono(
        self, stereo_audio: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Split stereo audio into two mono channels.

        Args:
            stereo_audio: Stereo audio array, shape (2, samples)

        Returns:
            Tuple of (left_mono, right_mono), each shape (samples,)

        Per spec (agents.md 2.3):
        - Stereo stems become TWO objects (two groups)
        - Split to mono WAV files
        """
        if stereo_audio.ndim != 2 or stereo_audio.shape[0] != 2:
            raise ValueError(
                f"Expected stereo audio shape (2, samples), "
                f"got {stereo_audio.shape}"
            )
        left = stereo_audio[0].astype(self.SAMPLE_FORMAT)
        right = stereo_audio[1].astype(self.SAMPLE_FORMAT)
        return left, right

    # ------------------------------------------------------------------
    # WAV writing
    # ------------------------------------------------------------------

    def write_mono_wav(self, audio: np.ndarray, output_path: str) -> None:
        """
        Write mono audio to WAV file (48 kHz, float32).

        Args:
            audio: Mono audio array, shape (samples,)
            output_path: Path to write WAV file
        """
        if audio.ndim != 1:
            raise ValueError(
                f"Expected mono audio shape (samples,), got {audio.shape}"
            )
        sf.write(
            output_path,
            audio.astype(self.SAMPLE_FORMAT),
            self.TARGET_SAMPLE_RATE,
            subtype="FLOAT",
        )
        logger.info("Wrote mono WAV: %s  (%d samples)", output_path, len(audio))

    def create_silent_wav(self, duration_seconds: float, output_path: str) -> None:
        """
        Create a silent WAV file.

        Args:
            duration_seconds: Duration of silent audio
            output_path: Path to write WAV file

        Per spec (agents.md 2.4):
        - Bed WAVs (1.1 through 10.1) are silent in v1
        - LFE.wav is silent in v1
        """
        num_samples = int(duration_seconds * self.TARGET_SAMPLE_RATE)
        silent_audio = np.zeros(num_samples, dtype=self.SAMPLE_FORMAT)
        sf.write(output_path, silent_audio, self.TARGET_SAMPLE_RATE, subtype="FLOAT")
        logger.info("Wrote silent WAV: %s  (%.2fs)", output_path, duration_seconds)

    def create_all_bed_wavs(self, duration_seconds: float, output_dir: str) -> None:
        """
        Create all required silent bed WAVs.

        Args:
            duration_seconds: Duration to match object audio
            output_dir: Directory to write bed WAVs

        Per spec (agents.md 2.4, 5):
        - Beds: 1.1, 2.1, 3.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1
        - LFE is special: 4.1 node -> LFE.wav file
        - All silent in v1
        """
        bed_ids = ["1.1", "2.1", "3.1", "5.1", "6.1", "7.1", "8.1", "9.1", "10.1"]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for bed_id in bed_ids:
            wav_path = output_path / f"{bed_id}.wav"
            self.create_silent_wav(duration_seconds, str(wav_path))

        # LFE special case
        lfe_path = output_path / "LFE.wav"
        self.create_silent_wav(duration_seconds, str(lfe_path))

        print(f"  Created {len(bed_ids) + 1} silent bed/LFE WAVs")

    # ------------------------------------------------------------------
    # Stem loading
    # ------------------------------------------------------------------

    def load_and_normalize_stem(
        self, stem_path: str
    ) -> Tuple[np.ndarray, int, int]:
        """
        Load a stem and normalize to 48 kHz float32.

        Args:
            stem_path: Path to input stem audio file

        Returns:
            Tuple of (normalized_audio, original_sr, num_channels)
            - normalized_audio shape: (samples,) for mono, (2, samples) for stereo
        """
        # Read audio as float32 using soundfile (preserves original gain)
        audio, original_sr = sf.read(stem_path, dtype="float32", always_2d=True)
        # soundfile returns shape (frames, channels) -- transpose to (channels, frames)
        audio = audio.T  # now (channels, samples)
        num_channels = audio.shape[0]

        logger.info(
            "Loaded %s: sr=%d ch=%d frames=%d",
            stem_path,
            original_sr,
            num_channels,
            audio.shape[1],
        )

        # Resample to 48 kHz
        audio = self.resample_to_48k(audio, original_sr)

        # Squeeze mono back to 1-D
        if num_channels == 1:
            audio = audio[0]

        return audio, original_sr, num_channels

    # ------------------------------------------------------------------
    # Per-stem processing
    # ------------------------------------------------------------------

    def process_stem(self, stem_info: dict, output_dir: str) -> None:
        """
        Process a single stem: load, normalize, split if stereo, write WAVs.

        Args:
            stem_info: Stem info dict from session manifest
            output_dir: Directory to write output WAVs
        """
        stem_path = stem_info["path"]
        wav_names = stem_info["wav_names"]

        audio, _original_sr, num_channels = self.load_and_normalize_stem(stem_path)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if num_channels == 1:
            out_file = output_path / wav_names[0]
            self.write_mono_wav(audio, str(out_file))
        elif num_channels == 2:
            left, right = self.split_stereo_to_mono(audio)
            self.write_mono_wav(left, str(output_path / wav_names[0]))
            self.write_mono_wav(right, str(output_path / wav_names[1]))
        else:
            raise ValueError(
                f"Unsupported channel count {num_channels} for {stem_path}"
            )

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def process_all_stems(self, manifest: dict, output_dir: str) -> None:
        """
        Process all stems from session manifest.

        Args:
            manifest: Session manifest dict
            output_dir: Directory to write all WAVs

        Pipeline:
        1. Process each stem (resample, split, write)
        2. Create silent bed/LFE WAVs matching longest stem duration
        """
        print("Stage 1: Normalize + Split Audio")

        stems = manifest["stems"]
        max_duration = manifest.get("max_duration_seconds", 300.0)

        for i, stem in enumerate(stems):
            print(f"  Processing stem {i + 1}/{len(stems)}: {stem['filename']}")
            self.process_stem(stem, output_dir)

        # Create silent bed WAVs matching the longest stem
        self.create_all_bed_wavs(max_duration, output_dir)

        print(f"  All audio normalized to {self.TARGET_SAMPLE_RATE} Hz")


# ======================================================================
# Utility functions
# ======================================================================


def compute_rms_db(audio: np.ndarray) -> float:
    """
    Compute RMS level in dB.

    Args:
        audio: Audio array

    Returns:
        RMS level in dB (or -200.0 for silence)

    Used for containsAudio.json generation.
    """
    rms = np.sqrt(np.mean(audio ** 2))
    if rms > 0:
        return float(20.0 * np.log10(rms))
    return -200.0
