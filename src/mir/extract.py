"""
SpatialSeed MIR (Music Information Retrieval) Extraction
=========================================================
Stage 2: MIR Extraction (Essentia)

Responsibilities:
- Extract per-stem global summary metrics using Essentia
- Compute features: loudness, spectral centroid, flux, onset density, etc.
- Extract stereo mix features (width, L/R energy balance)
- Write mir_summary.json
- Cache heavy computations (hash-based cache key)

Per spec: lowLevelSpecsV1.md § 7, agents.md § 8, § 13.1
"""

import numpy as np
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List


class MIRExtractor:
    """
    Extracts music information retrieval features using Essentia.
    
    Per spec (agents.md § 13.1):
    - Use Essentia for feature extraction
    - Cache results by audio hash
    - Support both per-stem and stereo mix features
    """
    
    def __init__(self, cache_dir: str = "cache/mir"):
        """
        Initialize MIR extractor.
        
        Args:
            cache_dir: Directory for caching MIR results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def compute_cache_key(self, audio_path: str, audio_hash: str) -> str:
        """
        Compute cache key for MIR features.
        
        Args:
            audio_path: Path to audio file
            audio_hash: Hash of audio file (from session manifest)
            
        Returns:
            Cache key string
        """
        return audio_hash
    
    def load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Load cached MIR features.
        
        Args:
            cache_key: Cache key string
            
        Returns:
            Cached features dict, or None if not found
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def save_to_cache(self, cache_key: str, features: Dict):
        """
        Save MIR features to cache.
        
        Args:
            cache_key: Cache key string
            features: Features dict to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(features, f, indent=2)
    
    def extract_stem_features(self, audio_path: str, audio_hash: str) -> Dict:
        """
        Extract MIR features for a single stem.
        
        Args:
            audio_path: Path to stem audio file
            audio_hash: Hash of audio file for caching
            
        Returns:
            Feature dict with keys:
            - loudness_lufs: Integrated LUFS loudness
            - spectral_centroid_mean: Mean spectral centroid (Hz)
            - spectral_centroid_std: Std dev of spectral centroid
            - spectral_flux_mean: Mean spectral flux
            - onset_density: Onset events per second
            - pitch_confidence_mean: Mean pitch detection confidence
            - harmonic_ratio: Ratio of harmonic to percussive energy
            - spectral_flatness_mean: Mean spectral flatness
            - zero_crossing_rate_mean: Mean zero crossing rate
            - rms_energy: RMS energy
            
        Per spec (agents.md § 13.1):
        - Use Essentia algorithms
        - Resample internally to 16 kHz for Essentia TF models if needed
        - Keep project audio at 48 kHz
        """
        # Check cache first
        cache_key = self.compute_cache_key(audio_path, audio_hash)
        cached = self.load_from_cache(cache_key)
        if cached is not None:
            print(f"    Loaded MIR features from cache: {audio_path}")
            return cached
        
        # TODO: Load audio (already normalized to 48 kHz)
        # TODO: Extract Essentia features:
        #   - Loudness (LUFS)
        #   - Spectral centroid (mean, std)
        #   - Spectral flux (mean)
        #   - Onset detection → onset density
        #   - Pitch detection → pitch confidence
        #   - HPSS → harmonic ratio
        #   - Spectral flatness
        #   - Zero crossing rate
        #   - RMS energy
        
        features = {
            "loudness_lufs": -23.0,  # ...placeholder...
            "spectral_centroid_mean": 2000.0,  # ...placeholder...
            "spectral_centroid_std": 500.0,  # ...placeholder...
            "spectral_flux_mean": 0.5,  # ...placeholder...
            "onset_density": 2.0,  # ...placeholder...
            "pitch_confidence_mean": 0.7,  # ...placeholder...
            "harmonic_ratio": 0.6,  # ...placeholder...
            "spectral_flatness_mean": 0.3,  # ...placeholder...
            "zero_crossing_rate_mean": 0.1,  # ...placeholder...
            "rms_energy": -20.0,  # ...placeholder...
        }
        
        # Save to cache
        self.save_to_cache(cache_key, features)
        
        return features
    
    def extract_stereo_mix_features(self, mix_path: str) -> Dict:
        """
        Extract stereo-specific features from reference mix.
        
        Args:
            mix_path: Path to stereo reference mix
            
        Returns:
            Feature dict with keys:
            - stereo_width: Stereo width measure
            - left_energy: Left channel RMS energy
            - right_energy: Right channel RMS energy
            - lr_correlation: Left/right channel correlation
            
        Used for placement heuristics.
        """
        # TODO: Load stereo mix
        # TODO: Compute stereo width (mid/side analysis)
        # TODO: Compute L/R energy balance
        # TODO: Compute L/R correlation
        
        features = {
            "stereo_width": 0.7,  # ...placeholder...
            "left_energy": -18.0,  # ...placeholder...
            "right_energy": -18.0,  # ...placeholder...
            "lr_correlation": 0.5,  # ...placeholder...
        }
        
        return features
    
    def extract_all_features(self, manifest: Dict, mix_path: Optional[str] = None) -> Dict:
        """
        Extract MIR features for all stems and optional mix.
        
        Args:
            manifest: Session manifest with stem info
            mix_path: Optional path to stereo reference mix
            
        Returns:
            MIR summary dict with per-stem and mix features
        """
        print("Stage 2: MIR Extraction (Essentia)")
        
        mir_summary = {
            "stems": {},
            "mix": None,
        }
        
        # Extract per-stem features
        stems = manifest["stems"]
        for i, stem in enumerate(stems):
            stem_name = stem["filename"]
            stem_path = stem["path"]
            stem_hash = stem.get("hash", "")
            
            print(f"  Extracting features for stem {i+1}/{len(stems)}: {stem_name}")
            features = self.extract_stem_features(stem_path, stem_hash)
            
            # Store by node IDs (multiple if stereo)
            for group_id in stem["group_ids"]:
                node_id = f"{group_id}.1"
                mir_summary["stems"][node_id] = {
                    "filename": stem_name,
                    "features": features,
                }
        
        # Extract mix features if provided
        if mix_path:
            print("  Extracting stereo mix features")
            mir_summary["mix"] = self.extract_stereo_mix_features(mix_path)
        
        return mir_summary
    
    def save_mir_summary(self, mir_summary: Dict, output_path: str):
        """
        Save MIR summary to JSON file.
        
        Args:
            mir_summary: MIR summary dict
            output_path: Path to write mir_summary.json
            
        Per spec (agents.md § 4.1):
        - mir_summary.json lives at package root
        - v1: MIR summaries only (not LUSID spectral_features yet)
        """
        with open(output_path, 'w') as f:
            json.dump(mir_summary, f, indent=2)
        
        print(f"  MIR summary saved to {output_path}")


def apply_mir_heuristics_for_category(features: Dict) -> Optional[str]:
    """
    Apply MIR-based heuristics to infer instrument category.
    
    Args:
        features: MIR features dict
        
    Returns:
        Inferred category string, or None if inconclusive
        
    Per spec (agents.md § 13.1):
    Heuristics:
    - bass: very low centroid + energy in low bands
    - drums/percussion: high onset density + high flux + low pitch confidence
    - fx/ambience: high spectral flatness + low onset density + high complexity
    - keys/guitar: high harmonicity + mid-range centroid
    """
    centroid = features.get("spectral_centroid_mean", 2000.0)
    onset_density = features.get("onset_density", 0.0)
    flux = features.get("spectral_flux_mean", 0.0)
    pitch_conf = features.get("pitch_confidence_mean", 0.0)
    flatness = features.get("spectral_flatness_mean", 0.0)
    harmonic_ratio = features.get("harmonic_ratio", 0.5)
    
    # TODO: Implement heuristics
    # - Check for bass: centroid < 200 Hz
    # - Check for drums: onset_density > 3.0 and pitch_conf < 0.3
    # - Check for fx: flatness > 0.6 and onset_density < 1.0
    # - Check for harmonic: harmonic_ratio > 0.7
    
    # ...placeholder...
    return None


def apply_mir_heuristics_for_role(features: Dict) -> Optional[str]:
    """
    Apply MIR-based heuristics to infer role hint.
    
    Args:
        features: MIR features dict
        
    Returns:
        Inferred role string, or None if inconclusive
        
    Similar logic to category heuristics but focused on role.
    """
    # TODO: Implement role heuristics
    # - percussion: high onset + low pitch
    # - bass: low centroid
    # - fx: high flatness + low onsets
    
    # ...placeholder...
    return None
