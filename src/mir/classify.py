"""
SpatialSeed Instrument Classification and Role Assignment
==========================================================
Stage 3: Classification + Role Assignment

Responsibilities:
- Classify stems into canonical categories
  (vocals, bass, drums, guitar, keys, pads, other, unknown)
- Assign role hints
  (bass, rhythm, lead, percussion, fx, unknown)
- Support deterministic fallbacks (filename hints, MIR heuristics)
- Allow user override in UI
- Cache classification results

Per spec: classify_README.md, agents.md 8, 13.1

NOTE on Essentia: The Essentia TF models (mtg_jamendo_instrument,
fs_loop_ds) are imported lazily so the rest of the pipeline works even
when essentia-tensorflow is not installed. When Essentia is unavailable
the classifier falls through to filename and MIR heuristic fallbacks
which are fully deterministic and require zero external models.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.mir.extract import apply_mir_heuristics_for_category, apply_mir_heuristics_for_role

logger = logging.getLogger("spatialSeed.mir.classify")


# ======================================================================
# Label-to-category mapping (agents.md 13.1)
# ======================================================================

_LABEL_TO_CATEGORY = {
    # vocals
    "voice": "vocals",
    # bass
    "bass": "bass",
    "doublebass": "bass",
    "acousticbassguitar": "bass",
    # drums
    "drums": "drums",
    "drummachine": "drums",
    "beat": "drums",
    # percussion
    "percussion": "percussion",
    "bongo": "percussion",
    # guitar
    "guitar": "guitar",
    "electricguitar": "guitar",
    "acousticguitar": "guitar",
    "classicalguitar": "guitar",
    # keys
    "piano": "keys",
    "electricpiano": "keys",
    "rhodes": "keys",
    "keyboard": "keys",
    "organ": "keys",
    "pipeorgan": "keys",
    # pads
    "pad": "pads",
    "synthesizer": "pads",
    # strings
    "strings": "strings",
    "violin": "strings",
    "cello": "strings",
    "viola": "strings",
    # fx / ambience (weak signals)
    "computer": "fx",
    "sampler": "fx",
}

# Role model label -> canonical role hint
_ROLE_LABEL_MAP = {
    "bass": "bass",
    "percussion": "percussion",
    "melody": "lead",
    "chords": "rhythm",
    "fx": "fx",
}


# ======================================================================
# Filename hint patterns
# ======================================================================

_FILENAME_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # (pattern, category, role_hint)
    # Vocals -- "LV" = lead vocal, "BV" = backing vocal
    (re.compile(r"\bvox\b|\bvocal\b|\bLV\b|\bBV\b|\bvoc\b", re.I), "vocals", "lead"),
    (re.compile(r"kick|snare|hat|drum|perc", re.I), "drums", "percussion"),
    (re.compile(r"bass", re.I), "bass", "bass"),
    # Guitar / acoustic -- "Aco" = acoustic, "gtr" = guitar
    (re.compile(r"gtr|guitar|\baco\b|acoustic", re.I), "guitar", "rhythm"),
    (re.compile(r"piano|keys|rhodes|organ", re.I), "keys", "rhythm"),
    (re.compile(r"string", re.I), "strings", "rhythm"),
    (re.compile(r"synth|pad", re.I), "pads", "rhythm"),
    (re.compile(r"fx|sfx|noise|ambient", re.I), "fx", "fx"),
]


class InstrumentClassifier:
    """
    Classifies stems using Essentia models (optional) and deterministic
    fallback heuristics.
    """

    CATEGORIES = [
        "vocals", "bass", "drums", "percussion",
        "guitar", "keys", "pads", "fx", "other", "unknown",
    ]
    ROLES = ["bass", "rhythm", "lead", "percussion", "fx", "unknown"]

    INSTRUMENT_MODEL = "mtg_jamendo_instrument-discogs-effnet"
    ROLE_MODEL = "fs_loop_ds-msd-musicnn"

    CATEGORY_THRESHOLD = 0.35
    CATEGORY_MARGIN = 0.05
    ROLE_THRESHOLD = 0.60

    def __init__(self, cache_dir: str = "cache/classify"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._essentia_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Essentia availability
    # ------------------------------------------------------------------

    def _check_essentia(self) -> bool:
        if self._essentia_available is None:
            try:
                import essentia  # noqa: F401
                import essentia.standard  # noqa: F401
                self._essentia_available = True
                logger.info("Essentia is available")
            except ImportError:
                self._essentia_available = False
                logger.warning(
                    "essentia-tensorflow not installed; "
                    "classification will use fallbacks only"
                )
        return self._essentia_available

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def load_from_cache(self, audio_hash: str) -> Optional[Dict]:
        cache_file = self.cache_dir / f"{audio_hash}.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        return None

    def save_to_cache(self, audio_hash: str, result: Dict) -> None:
        cache_file = self.cache_dir / f"{audio_hash}.json"
        with open(cache_file, "w") as f:
            json.dump(result, f, indent=2)

    # ------------------------------------------------------------------
    # Essentia model runners
    # ------------------------------------------------------------------

    def run_essentia_instrument_classifier(self, wav_path: str) -> List[Dict]:
        """
        Run Essentia MTG-Jamendo instrument classifier (multi-label, 40 classes).
        Resamples internally to 16 kHz.

        Returns list of {label, p} sorted descending by probability.
        """
        import essentia.standard as es

        audio = es.MonoLoader(filename=wav_path, sampleRate=16000)()

        model = es.TensorflowPredictEffnetDiscogs(
            graphFilename="essentia/test/models/discogs-effnet-bs64-1.pb",
            output="PartitionedCall:1",
        )
        embeddings = model(audio)

        classifier = es.TensorflowPredict2D(
            graphFilename="essentia/test/models/mtg_jamendo_instrument-discogs-effnet-1.pb",
            output="model/Softmax",
        )
        predictions = classifier(embeddings)

        # Average across time frames
        mean_preds = predictions.mean(axis=0)

        # Build label list (the model metadata provides labels; use known ordering)
        # TODO: load labels from model metadata json when available
        # For now return raw index-probability pairs
        results = [{"label": f"class_{i}", "p": float(p)} for i, p in enumerate(mean_preds)]
        results.sort(key=lambda x: x["p"], reverse=True)
        return results

    def run_essentia_role_classifier(self, wav_path: str) -> Dict:
        """
        Run Essentia Freesound Loop role classifier (5 classes).
        """
        import essentia.standard as es

        audio = es.MonoLoader(filename=wav_path, sampleRate=16000)()

        model = es.TensorflowPredictMusiCNN(
            graphFilename="essentia/test/models/fs_loop_ds-msd-musicnn-1.pb",
            output="model/Softmax",
        )
        predictions = model(audio)
        mean_preds = predictions.mean(axis=0)

        # Known label order for fs_loop_ds
        labels = ["bass", "chords", "fx", "melody", "percussion"]
        role_probs = {label: float(mean_preds[i]) for i, label in enumerate(labels)}
        return role_probs

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def map_instrument_to_category(
        self, predictions: List[Dict]
    ) -> Tuple[str, float]:
        """
        Map raw instrument predictions to canonical category.

        Per spec (agents.md 13.1):
        - Accumulate max probability per category
        - Accept if score >= threshold and margin over second-best >= margin
        """
        category_scores: Dict[str, float] = {}
        for pred in predictions:
            label = pred["label"].lower().replace(" ", "")
            cat = _LABEL_TO_CATEGORY.get(label)
            if cat is None:
                continue
            if cat not in category_scores or pred["p"] > category_scores[cat]:
                category_scores[cat] = pred["p"]

        if not category_scores:
            return "unknown", 0.0

        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        best_cat, best_score = sorted_cats[0]
        second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0.0

        if best_score >= self.CATEGORY_THRESHOLD and (best_score - second_score) >= self.CATEGORY_MARGIN:
            return best_cat, best_score

        return "unknown", best_score

    def map_role_to_hint(self, role_probs: Dict) -> Tuple[str, float]:
        """
        Map role model output to canonical role hint.
        """
        best_label = max(role_probs, key=role_probs.get)  # type: ignore[arg-type]
        best_prob = role_probs[best_label]
        hint = _ROLE_LABEL_MAP.get(best_label, "unknown")
        if best_prob >= self.ROLE_THRESHOLD:
            return hint, best_prob
        return "unknown", best_prob

    # ------------------------------------------------------------------
    # Deterministic fallbacks
    # ------------------------------------------------------------------

    def apply_filename_fallback(self, stem_name: str) -> Optional[Tuple[str, str]]:
        """
        Apply filename-based heuristics (highest leverage, deterministic).

        Per spec (agents.md 13.1 C.1).
        """
        for pattern, category, role in _FILENAME_PATTERNS:
            if pattern.search(stem_name):
                logger.info("Filename fallback matched: %s -> %s", stem_name, category)
                return category, role
        return None

    def apply_mir_fallback(self, mir_features: Dict) -> Optional[Tuple[str, str]]:
        """
        Apply MIR-based heuristics.

        Per spec (agents.md 13.1 C.2).
        """
        cat = apply_mir_heuristics_for_category(mir_features)
        role = apply_mir_heuristics_for_role(mir_features)
        if cat is not None:
            return cat, role or "unknown"
        return None

    # ------------------------------------------------------------------
    # Single node classification
    # ------------------------------------------------------------------

    def classify_node(
        self,
        wav_path: str,
        node_id: str,
        stem_name: Optional[str] = None,
        mir_features: Optional[Dict] = None,
        audio_hash: Optional[str] = None,
    ) -> Dict:
        """
        Classify a single audio node.

        Returns classification result dict per classify_README.md contract.
        """
        # Cache check
        if audio_hash:
            cached = self.load_from_cache(audio_hash)
            if cached:
                logger.info("Classification cache hit: %s", node_id)
                return cached

        result: Dict = {
            "node_id": node_id,
            "category": "unknown",
            "category_confidence": 0.0,
            "role_hint": "unknown",
            "role_confidence": 0.0,
            "top_labels": [],
            "backend": {
                "instrument_model": self.INSTRUMENT_MODEL,
                "role_model": self.ROLE_MODEL,
            },
            "fallbacks_used": [],
        }

        # --- Try Essentia models first ------------------------------------
        if self._check_essentia():
            try:
                instrument_preds = self.run_essentia_instrument_classifier(wav_path)
                result["top_labels"] = instrument_preds[:5]
                cat, cat_conf = self.map_instrument_to_category(instrument_preds)
                role_probs = self.run_essentia_role_classifier(wav_path)
                role_hint, role_conf = self.map_role_to_hint(role_probs)

                if cat_conf >= self.CATEGORY_THRESHOLD:
                    result["category"] = cat
                    result["category_confidence"] = cat_conf
                if role_conf >= self.ROLE_THRESHOLD:
                    result["role_hint"] = role_hint
                    result["role_confidence"] = role_conf
            except Exception as exc:
                logger.warning("Essentia classification failed for %s: %s", node_id, exc)
                result["fallbacks_used"].append("essentia_error")

        # --- Fallback 1: filename hints -----------------------------------
        if result["category"] == "unknown" and stem_name:
            fn_result = self.apply_filename_fallback(stem_name)
            if fn_result:
                result["category"] = fn_result[0]
                if result["role_hint"] == "unknown":
                    result["role_hint"] = fn_result[1]
                result["fallbacks_used"].append("filename")

        # --- Fallback 2: MIR heuristics -----------------------------------
        if result["category"] == "unknown" and mir_features:
            mir_result = self.apply_mir_fallback(mir_features)
            if mir_result:
                result["category"] = mir_result[0]
                if result["role_hint"] == "unknown":
                    result["role_hint"] = mir_result[1]
                result["fallbacks_used"].append("mir_heuristic")

        if not result["fallbacks_used"]:
            result["fallbacks_used"].append("none")

        # Cache
        if audio_hash:
            self.save_to_cache(audio_hash, result)

        return result

    # ------------------------------------------------------------------
    # Batch classification
    # ------------------------------------------------------------------

    def classify_all_stems(
        self, manifest: Dict, mir_summary: Dict, wav_dir: str
    ) -> Dict:
        """
        Classify all stems from manifest.

        Returns classification results dict keyed by node_id.
        """
        print("Stage 3: Classification + Role Assignment")

        results: Dict = {}
        stems = manifest["stems"]

        for i, stem in enumerate(stems):
            stem_name = stem["filename"]
            stem_hash = stem.get("hash", "")

            print(f"  Classifying stem {i + 1}/{len(stems)}: {stem_name}")

            for j, (group_id, wav_name) in enumerate(
                zip(stem["group_ids"], stem["wav_names"])
            ):
                node_id = f"{group_id}.1"
                wav_path = str(Path(wav_dir) / wav_name)

                mir_features = (
                    mir_summary.get("stems", {})
                    .get(node_id, {})
                    .get("features", {})
                )

                display_name = stem_name if j == 0 else f"{stem_name} (R)"

                result = self.classify_node(
                    wav_path=wav_path,
                    node_id=node_id,
                    stem_name=display_name,
                    mir_features=mir_features,
                    audio_hash=stem_hash,
                )

                results[node_id] = result
                print(
                    f"    {node_id}: {result['category']} "
                    f"(role={result['role_hint']}, "
                    f"fallbacks={result['fallbacks_used']})"
                )

        return results
