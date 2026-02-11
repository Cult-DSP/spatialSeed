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

Per spec: lowLevelSpecsV1.md § 7, agents.md § 2.1, 2.4
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import warnings


class AudioNormalizer:
    """
    Handles audio resampling, stereo splitting, and WAV generation.
    
    Per spec (agents.md § 2.1):
    - Target: 48 kHz, float32, mono
    - NO gain changes (no LUFS/peak normalization in v1)
    """
    
    TARGET_SAMPLE_RATE = 48000
    SAMPLE_FORMAT = np.float32  # v1: float32 (TODO: revisit int16 later)
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize audio normalizer.
        
        Args:
            cache_dir: Optional directory for caching processed audio
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
    def resample_to_48k(self, audio: np.ndarray, original_sr: int) -> np.ndarray:
        """
        Resample audio to 48 kHz.
        
        Args:
            audio: Input audio array (channels, samples) or (samples,)
            original_sr: Original sample rate
            
        Returns:
            Resampled audio at 48 kHz
            
        Per spec (agents.md § 13.1):
        - Resample only, NO gain changes
        - Use high-quality resampling (librosa or scipy)
        """
        if original_sr == self.TARGET_SAMPLE_RATE:
            return audio
        
        # TODO: Implement high-quality resampling
        #   - Use librosa.resample() or scipy.signal.resample_poly()
        #   - Preserve audio shape (mono vs stereo)
        #   - Log resampling operation
        
        resampled = audio  # ...placeholder...
        return resampled
    
    def split_stereo_to_mono(self, stereo_audio: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Split stereo audio into two mono channels.
        
        Args:
            stereo_audio: Stereo audio array, shape (2, samples)
            
        Returns:
            Tuple of (left_mono, right_mono)
            
        Per spec (agents.md § 2.3):
        - Stereo stems become TWO objects (two groups)
        - Split to mono WAV files
        """
        if stereo_audio.ndim != 2 or stereo_audio.shape[0] != 2:
            raise ValueError(f"Expected stereo audio (2, samples), got shape {stereo_audio.shape}")
        
        left = stereo_audio[0]
        right = stereo_audio[1]
        
        return left, right
    
    def create_silent_wav(self, duration_seconds: float, output_path: str):
        """
        Create a silent WAV file.
        
        Args:
            duration_seconds: Duration of silent audio
            output_path: Path to write WAV file
            
        Per spec (agents.md § 2.4):
        - Bed WAVs (1.1 through 10.1) are silent in v1
        - LFE.wav is silent in v1
        - This is for ADM compatibility; TODO: remove constraint later
        """
        num_samples = int(duration_seconds * self.TARGET_SAMPLE_RATE)
        silent_audio = np.zeros(num_samples, dtype=self.SAMPLE_FORMAT)
        
        # TODO: Write WAV using scipy.io.wavfile or soundfile
        #   - Sample rate: 48000
        #   - Format: float32
        # TODO: Log creation
        
        pass
    
    def create_all_bed_wavs(self, duration_seconds: float, output_dir: str):
        """
        Create all required silent bed WAVs.
        
        Args:
            duration_seconds: Duration to match object audio
            output_dir: Directory to write bed WAVs
            
        Per spec (agents.md § 2.4, § 5):
        - Always include bed groups 1-10 for ADM compatibility
        - Beds: 1.1, 2.1, 3.1, 5.1, 6.1, 7.1, 8.1, 9.1, 10.1
        - LFE is special: 4.1 node → LFE.wav file
        - All silent in v1
        """
        bed_ids = ["1.1", "2.1", "3.1", "5.1", "6.1", "7.1", "8.1", "9.1", "10.1"]
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create bed WAVs
        for bed_id in bed_ids:
            wav_path = output_path / f"{bed_id}.wav"
            self.create_silent_wav(duration_seconds, str(wav_path))
        
        # Create LFE.wav (special case)
        lfe_path = output_path / "LFE.wav"
        self.create_silent_wav(duration_seconds, str(lfe_path))
        
        print(f"  Created {len(bed_ids) + 1} silent bed/LFE WAVs")
    
    def load_and_normalize_stem(self, stem_path: str) -> Tuple[np.ndarray, int, int]:
        """
        Load a stem and normalize to 48 kHz.
        
        Args:
            stem_path: Path to input stem WAV
            
        Returns:
            Tuple of (normalized_audio, original_sr, num_channels)
            
        Where:
            normalized_audio: Audio resampled to 48 kHz, shape (channels, samples) or (samples,)
            original_sr: Original sample rate
            num_channels: Number of channels (1 or 2)
        """
        # TODO: Load audio using librosa or soundfile
        #   - Get audio array and sample rate
        #   - Determine number of channels
        # TODO: Resample to 48 kHz
        # TODO: Return normalized audio + metadata
        
        audio = None  # ...placeholder...
        original_sr = 44100  # ...placeholder...
        num_channels = 1  # ...placeholder...
        
        return audio, original_sr, num_channels
    
    def write_mono_wav(self, audio: np.ndarray, output_path: str):
        """
        Write mono audio to WAV file.
        
        Args:
            audio: Mono audio array
            output_path: Path to write WAV file
            
        Per spec (agents.md § 2.1):
        - 48 kHz, float32
        """
        if audio.ndim != 1:
            raise ValueError(f"Expected mono audio (samples,), got shape {audio.shape}")
        
        # TODO: Write WAV using scipy.io.wavfile or soundfile
        #   - Sample rate: 48000
        #   - Format: float32
        # TODO: Log write operation
        
        pass
    
    def process_stem(self, stem_info: dict, output_dir: str):
        """
        Process a single stem: load, normalize, split if stereo, write WAVs.
        
        Args:
            stem_info: Stem info dict from session manifest (includes group_ids, wav_names)
            output_dir: Directory to write output WAVs
            
        Pipeline:
        1. Load stem audio
        2. Resample to 48 kHz
        3. If stereo: split to L/R mono
        4. Write mono WAV(s) with deterministic names
        """
        stem_path = stem_info["path"]
        wav_names = stem_info["wav_names"]
        
        # Load and normalize
        audio, original_sr, num_channels = self.load_and_normalize_stem(stem_path)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if num_channels == 1:
            # Mono stem: write single WAV
            out_file = output_path / wav_names[0]
            self.write_mono_wav(audio, str(out_file))
            
        elif num_channels == 2:
            # Stereo stem: split and write two WAVs
            left, right = self.split_stereo_to_mono(audio)
            
            out_left = output_path / wav_names[0]
            out_right = output_path / wav_names[1]
            
            self.write_mono_wav(left, str(out_left))
            self.write_mono_wav(right, str(out_right))
        
        else:
            raise ValueError(f"Unsupported channel count {num_channels} for stem {stem_path}")
    
    def process_all_stems(self, manifest: dict, output_dir: str):
        """
        Process all stems from session manifest.
        
        Args:
            manifest: Session manifest dict
            output_dir: Directory to write all WAVs
            
        Pipeline:
        1. Process each stem (resample, split, write)
        2. Create silent bed/LFE WAVs
        """
        print("Stage 1: Normalize + Split Audio")
        
        stems = manifest["stems"]
        
        # Process each stem
        for i, stem in enumerate(stems):
            print(f"  Processing stem {i+1}/{len(stems)}: {stem['filename']}")
            self.process_stem(stem, output_dir)
        
        # Create silent beds
        # TODO: Determine duration from longest stem
        max_duration = 300.0  # ...placeholder...
        self.create_all_bed_wavs(max_duration, output_dir)
        
        print(f"  All audio normalized to {self.TARGET_SAMPLE_RATE} Hz")


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
        return 20 * np.log10(rms)
    else:
        return -200.0
