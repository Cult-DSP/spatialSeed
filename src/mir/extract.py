"""
SpatialSeed MIR (Music Information Retrieval) Extraction
=========================================================
Stage 2: MIR Extraction

Responsibilities:
- Extract per-stem global summary metrics using librosa
- Compute features: loudness, spectral centroid, flux, onset density, etc.
- Extract stereo mix features (width, L/R energy balance)
- Write mir_summary.json
- Cache heavy computations (hash-based cache key)

Per spec: lowLevelSpecsV1.md 7, agents.md 8, 13.1

NOTE: This implementation uses librosa for all feature extraction. Essentia
is reserved for the classification stage (mir/classify.py) where its
TensorFlow models are required. librosa is permissively licensed (ISC) and
provides all the summary features we need here.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger("spatialSeed.mir.extract")


class MIRExtractor:
    """
    Extracts music information retrieval features using librosa.

    Per spec (agents.md 13.1):
    - Cache results by audio hash
    - Support both per-stem and stereo mix features
    """

    def __init__(self, cache_dir: str = "cache/mir"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def compute_cache_key(self, audio_path: str, audio_hash: str) -> str:
        return audio_hash

    def load_from_cache(self, cache_key: str) -> Optional[Dict]:
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        return None

    def save_to_cache(self, cache_key: str, features: Dict) -> None:
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            json.dump(features, f, indent=2)

    # ------------------------------------------------------------------
    # Per-stem feature extraction
    # ------------------------------------------------------------------

    def extract_stem_features(self, audio_path: str, audio_hash: str) -> Dict:
        """
        Extract MIR features for a single mono stem (already 48 kHz).

        Returns a flat dict of scalar summary features suitable for JSON
        serialisation and downstream heuristic classification.
        """
        # Cache check
        cache_key = self.compute_cache_key(audio_path, audio_hash)
        cached = self.load_from_cache(cache_key)
        if cached is not None:
            logger.info("MIR cache hit: %s", audio_path)
            return cached

        # Load audio -------------------------------------------------------
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)

        # -- RMS energy ----------------------------------------------------
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_db = float(20.0 * np.log10(rms_mean)) if rms_mean > 0 else -200.0

        # -- Spectral centroid ---------------------------------------------
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        centroid_mean = float(np.mean(cent))
        centroid_std = float(np.std(cent))

        # -- Spectral flux (onset strength envelope) -----------------------
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        flux_mean = float(np.mean(oenv))

        # -- Onset density -------------------------------------------------
        onsets = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=oenv)
        onset_density = float(len(onsets) / duration) if duration > 0 else 0.0

        # -- Pitch confidence (via piptrack) -------------------------------
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        # confidence ~ fraction of frames with a detected pitch above threshold
        pitch_detected = (magnitudes.max(axis=0) > 0).astype(float)
        pitch_confidence_mean = float(np.mean(pitch_detected))

        # -- HPSS harmonic ratio -------------------------------------------
        y_harm, y_perc = librosa.effects.hpss(y)
        harm_energy = float(np.mean(y_harm ** 2))
        perc_energy = float(np.mean(y_perc ** 2))
        total_energy = harm_energy + perc_energy
        harmonic_ratio = (
            float(harm_energy / total_energy) if total_energy > 0 else 0.5
        )

        # -- Spectral flatness ---------------------------------------------
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        flatness_mean = float(np.mean(flatness))

        # -- Zero crossing rate --------------------------------------------
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = float(np.mean(zcr))

        features: Dict = {
            "duration_seconds": round(duration, 4),
            "rms_energy": round(rms_db, 2),
            "spectral_centroid_mean": round(centroid_mean, 2),
            "spectral_centroid_std": round(centroid_std, 2),
            "spectral_flux_mean": round(flux_mean, 4),
            "onset_density": round(onset_density, 4),
            "pitch_confidence_mean": round(pitch_confidence_mean, 4),
            "harmonic_ratio": round(harmonic_ratio, 4),
            "spectral_flatness_mean": round(flatness_mean, 6),
            "zero_crossing_rate_mean": round(zcr_mean, 6),
        }

        # Persist cache
        self.save_to_cache(cache_key, features)
        logger.info("Extracted MIR features for %s", audio_path)
        return features

    # ------------------------------------------------------------------
    # Stereo mix features
    # ------------------------------------------------------------------

    def extract_stereo_mix_features(self, mix_path: str) -> Dict:
        """
        Extract stereo-specific features from a reference mix.
        Used for placement heuristics.
        """
        audio, sr = sf.read(mix_path, dtype="float32", always_2d=True)
        # shape (frames, channels)
        if audio.shape[1] < 2:
            logger.warning("Reference mix is mono; stereo features will be trivial")
            left = audio[:, 0]
            right = audio[:, 0]
        else:
            left = audio[:, 0]
            right = audio[:, 1]

        mid = (left + right) / 2.0
        side = (left - right) / 2.0

        mid_energy = float(np.mean(mid ** 2))
        side_energy = float(np.mean(side ** 2))
        total = mid_energy + side_energy
        stereo_width = float(side_energy / total) if total > 0 else 0.0

        left_rms = float(np.sqrt(np.mean(left ** 2)))
        right_rms = float(np.sqrt(np.mean(right ** 2)))

        # Pearson correlation between L and R
        if np.std(left) > 0 and np.std(right) > 0:
            lr_corr = float(np.corrcoef(left, right)[0, 1])
        else:
            lr_corr = 1.0

        features = {
            "stereo_width": round(stereo_width, 4),
            "left_energy": round(
                float(20 * np.log10(left_rms)) if left_rms > 0 else -200.0, 2
            ),
            "right_energy": round(
                float(20 * np.log10(right_rms)) if right_rms > 0 else -200.0, 2
            ),
            "lr_correlation": round(lr_corr, 4),
        }
        return features

    # ------------------------------------------------------------------
    # Batch extraction
    # ------------------------------------------------------------------

    def extract_all_features(
        self, manifest: Dict, mix_path: Optional[str] = None
    ) -> Dict:
        """
        Extract MIR features for all stems (and optional mix).

        Args:
            manifest: Session manifest with stem info
            mix_path: Optional path to stereo reference mix

        Returns:
            MIR summary dict with per-stem and mix features
        """
        print("Stage 2: MIR Extraction")

        mir_summary: Dict = {
            "stems": {},
            "mix": None,
        }

        stems = manifest["stems"]
        for i, stem in enumerate(stems):
            stem_name = stem["filename"]
            stem_hash = stem.get("hash", "")

            print(f"  Extracting features for stem {i + 1}/{len(stems)}: {stem_name}")

            # For each node produced by this stem
            for j, (group_id, wav_name) in enumerate(
                zip(stem["group_ids"], stem["wav_names"])
            ):
                node_id = f"{group_id}.1"

                # The normalised mono WAV lives alongside beds in the work dir.
                # Caller is expected to pass actual wav paths; we try the stem
                # source path as fallback for feature extraction.
                wav_path = stem.get("_wav_path_override")
                if wav_path is None:
                    wav_path = stem["path"]

                features = self.extract_stem_features(wav_path, stem_hash)
                mir_summary["stems"][node_id] = {
                    "filename": stem_name,
                    "features": features,
                }

        # Stereo mix features
        if mix_path:
            print("  Extracting stereo mix features")
            mir_summary["mix"] = self.extract_stereo_mix_features(mix_path)

        return mir_summary

    def save_mir_summary(self, mir_summary: Dict, output_path: str) -> None:
        """
        Save MIR summary to JSON file.

        Per spec (agents.md 4.1):
        - mir_summary.json lives at package root
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(mir_summary, f, indent=2)
        print(f"  MIR summary saved to {output_path}")


# ======================================================================
# Heuristic helpers (used by classify.py)
# ======================================================================


def apply_mir_heuristics_for_category(features: Dict) -> Optional[str]:
    """
    Apply MIR-based heuristics to infer instrument category.

    Per spec (agents.md 13.1 C.2):
    - bass: low centroid, high harmonicity
    - drums/percussion: high onset density + low pitch confidence, OR
      high centroid + low harmonic ratio
    - fx/ambience: high spectral flatness + low onset density
    - vocals: very high pitch confidence + mid-high centroid + sparse onsets
    - strings: very high pitch confidence + high onset density (bowed micro-onsets)
    - guitar: mid centroid + moderate onsets + high harmonicity
    - keys: remaining harmonic content

    Thresholds tuned against real stems (96 kHz stereo, librosa features).
    """
    centroid = features.get("spectral_centroid_mean", 2000.0)
    onset_density = features.get("onset_density", 0.0)
    flux = features.get("spectral_flux_mean", 0.0)
    pitch_conf = features.get("pitch_confidence_mean", 0.0)
    flatness = features.get("spectral_flatness_mean", 0.0)
    harmonic_ratio = features.get("harmonic_ratio", 0.5)

    # Bass: low centroid with reasonable harmonicity
    if centroid < 1000 and harmonic_ratio > 0.8 and pitch_conf > 0.6:
        return "bass"

    # Drums / percussion: high onset density + low pitch confidence
    if onset_density > 2.5 and pitch_conf < 0.5 and centroid > 2000:
        return "drums"

    # Percussion (sparse): low harmonic ratio
    if harmonic_ratio < 0.3:
        return "drums"

    # FX / ambience: flat spectrum, sparse events
    if flatness > 0.1 and onset_density < 1.0 and harmonic_ratio < 0.4:
        return "fx"

    # --- Harmonic content zone (harmonic_ratio > 0.65) ---
    if harmonic_ratio > 0.65:

        # Strings: very high pitch confidence + very high onset density
        # (bowed strings produce many micro-onsets from vibrato/bow changes)
        if pitch_conf > 0.9 and onset_density > 8.0 and centroid > 1500:
            return "strings"

        # Vocals: very high pitch confidence + mid-high centroid + sparse onsets
        if pitch_conf > 0.9 and centroid > 2000 and onset_density < 3.0:
            return "vocals"

        # Guitar / acoustic: lower centroid, moderate onsets, very harmonic
        if harmonic_ratio > 0.9 and 800 < centroid < 2000 and onset_density > 2.0:
            return "guitar"

        # Keys: everything else harmonic
        if 500 < centroid < 6000:
            return "keys"

    return None


def apply_mir_heuristics_for_role(features: Dict) -> Optional[str]:
    """
    Apply MIR-based heuristics to infer role hint.
    """
    centroid = features.get("spectral_centroid_mean", 2000.0)
    onset_density = features.get("onset_density", 0.0)
    pitch_conf = features.get("pitch_confidence_mean", 0.0)
    flatness = features.get("spectral_flatness_mean", 0.0)
    harmonic_ratio = features.get("harmonic_ratio", 0.5)

    if centroid < 1000 and harmonic_ratio > 0.8:
        return "bass"
    if onset_density > 2.5 and pitch_conf < 0.5:
        return "percussion"
    if harmonic_ratio < 0.3:
        return "percussion"
    if flatness > 0.1 and onset_density < 1.0 and harmonic_ratio < 0.4:
        return "fx"
    # Vocals: very high pitch confidence, mid-high centroid, sparse onsets
    if pitch_conf > 0.9 and centroid > 2000 and onset_density < 3.0:
        return "lead"
    # Rhythm: moderate onsets in harmonic zone
    if harmonic_ratio > 0.65 and onset_density > 2.0:
        return "rhythm"

    return None
