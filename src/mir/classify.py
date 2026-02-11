"""
SpatialSeed Instrument Classification and Role Assignment
==========================================================
Stage 3: Classification + Role Assignment

Responsibilities:
- Classify stems into canonical categories (vocals, bass, drums, guitar, keys, pads, other, unknown)
- Assign role hints (bass, rhythm/harmony, lead, percussion/drums, fx/ambience, unknown)
- Support deterministic fallbacks (filename hints, MIR heuristics)
- Allow user override in UI
- Cache classification results

Per spec: classify_README.md, agents.md § 8, § 13.1
"""

import json
from pathlib import Path
from typing import Dict, Optional, List


class InstrumentClassifier:
    """
    Classifies stems using Essentia models and fallback heuristics.
    
    Per spec (classify_README.md, agents.md § 13.1):
    Default backend (v1):
    - Instrument category: mtg_jamendo_instrument-discogs-effnet (multi-label)
    - Role hint: fs_loop_ds-msd-musicnn (single-label)
    
    Thresholds (initial defaults):
    - Instrument category: accept if score >= 0.35 and margin >= 0.05
    - Role: accept if max(prob) >= 0.60
    """
    
    # Canonical categories
    CATEGORIES = ["vocals", "bass", "drums", "guitar", "keys", "pads", "other", "unknown"]
    
    # Role hints
    ROLES = ["bass", "rhythm", "lead", "percussion", "fx", "unknown"]
    
    # Model configuration
    INSTRUMENT_MODEL = "mtg_jamendo_instrument-discogs-effnet"
    ROLE_MODEL = "fs_loop_ds-msd-musicnn"
    
    # Thresholds
    CATEGORY_THRESHOLD = 0.35
    CATEGORY_MARGIN = 0.05
    ROLE_THRESHOLD = 0.60
    
    def __init__(self, cache_dir: str = "cache/classify"):
        """
        Initialize classifier.
        
        Args:
            cache_dir: Directory for caching classification results
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_from_cache(self, audio_hash: str) -> Optional[Dict]:
        """Load cached classification result."""
        cache_file = self.cache_dir / f"{audio_hash}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def save_to_cache(self, audio_hash: str, result: Dict):
        """Save classification result to cache."""
        cache_file = self.cache_dir / f"{audio_hash}.json"
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    def run_essentia_instrument_classifier(self, wav_path: str) -> List[Dict]:
        """
        Run Essentia MTG-Jamendo instrument classifier.
        
        Args:
            wav_path: Path to mono stem WAV (48 kHz)
            
        Returns:
            List of {"label": str, "p": float} dicts sorted by probability
            
        Per spec (agents.md § 13.1):
        - Model: mtg_jamendo_instrument-discogs-effnet
        - Multi-label output (40 classes)
        - Resample internally to 16 kHz for Essentia TF model
        """
        # TODO: Load audio
        # TODO: Resample to 16 kHz for Essentia model
        # TODO: Load Essentia model from essentia/test/models/
        # TODO: Run inference
        # TODO: Return sorted label probabilities
        
        # ...placeholder...
        predictions = [
            {"label": "voice", "p": 0.91},
            {"label": "drums", "p": 0.23},
            {"label": "guitar", "p": 0.15},
        ]
        
        return predictions
    
    def run_essentia_role_classifier(self, wav_path: str) -> Dict:
        """
        Run Essentia Freesound Loop role classifier.
        
        Args:
            wav_path: Path to mono stem WAV (48 kHz)
            
        Returns:
            Dict of {"bass": p, "chords": p, "fx": p, "melody": p, "percussion": p}
            
        Per spec (agents.md § 13.1):
        - Model: fs_loop_ds-msd-musicnn
        - Single-label output (5 classes)
        """
        # TODO: Load audio
        # TODO: Resample to 16 kHz for Essentia model
        # TODO: Load Essentia model from essentia/test/models/
        # TODO: Run inference
        # TODO: Return role probabilities
        
        # ...placeholder...
        role_probs = {
            "bass": 0.05,
            "chords": 0.10,
            "fx": 0.02,
            "melody": 0.78,
            "percussion": 0.05,
        }
        
        return role_probs
    
    def map_instrument_to_category(self, predictions: List[Dict]) -> tuple[str, float]:
        """
        Map raw instrument predictions to canonical category.
        
        Args:
            predictions: List of {"label": str, "p": float} from Essentia
            
        Returns:
            Tuple of (category, confidence)
            
        Per spec (agents.md § 13.1):
        Category mapping:
        - vocals: voice
        - bass: bass, doublebass, acousticbassguitar
        - drums: drums, drummachine, beat
        - percussion: percussion, bongo
        - guitar: guitar, electricguitar, acousticguitar, classicalguitar
        - keys: piano, electricpiano, rhodes, keyboard, organ, pipeorgan
        - pads: pad, synthesizer, strings (optional)
        - fx/ambience: computer, sampler (weak signal)
        - else: other
        """
        # Build category scores
        category_scores = {cat: 0.0 for cat in self.CATEGORIES}
        
        # TODO: For each prediction:
        #   - Map label to category
        #   - Accumulate max probability per category
        # TODO: Choose category with highest score
        # TODO: Check acceptance threshold and margin
        
        # ...placeholder...
        best_category = "vocals"
        best_score = 0.91
        
        return best_category, best_score
    
    def map_role_to_hint(self, role_probs: Dict) -> tuple[str, float]:
        """
        Map role model output to role hint.
        
        Args:
            role_probs: Dict of role probabilities from Essentia
            
        Returns:
            Tuple of (role_hint, confidence)
            
        Per spec (agents.md § 13.1):
        Role mapping:
        - bass → bass
        - percussion → percussion/drums
        - melody → lead
        - chords → rhythm/harmony
        - fx → fx/ambience
        """
        # TODO: Map role labels to canonical role hints
        # TODO: Choose role with highest probability
        # TODO: Check acceptance threshold
        
        # ...placeholder...
        best_role = "lead"
        best_prob = 0.78
        
        return best_role, best_prob
    
    def apply_filename_fallback(self, stem_name: str) -> Optional[tuple[str, str]]:
        """
        Apply filename-based heuristics.
        
        Args:
            stem_name: Stem filename
            
        Returns:
            Tuple of (category, role_hint), or None if no match
            
        Per spec (agents.md § 13.1):
        Filename hints (highest leverage, deterministic):
        - vox, vocal → vocals
        - kick, snare, hat, drum, perc → drums/percussion
        - bass → bass
        - gtr, guitar → guitar
        - piano, keys, rhodes, organ, synth, pad → keys/pads
        """
        name_lower = stem_name.lower()
        
        # TODO: Check for filename patterns
        # TODO: Return (category, role_hint) if match found
        
        # ...placeholder...
        return None
    
    def apply_mir_fallback(self, mir_features: Dict) -> Optional[tuple[str, str]]:
        """
        Apply MIR-based heuristics.
        
        Args:
            mir_features: MIR features dict
            
        Returns:
            Tuple of (category, role_hint), or None if inconclusive
            
        Per spec (agents.md § 13.1):
        MIR heuristics:
        - bass: centroid very low + energy in low bands
        - drums/percussion: high onset density + high flux + low pitch confidence
        - fx/ambience: high spectral flatness + low onset density + high complexity
        - keys/guitar: high harmonicity + mid-range centroid
        """
        # TODO: Apply MIR heuristics (see mir/extract.py helpers)
        
        # ...placeholder...
        return None
    
    def classify_node(self, wav_path: str, node_id: str, 
                     stem_name: Optional[str] = None,
                     mir_features: Optional[Dict] = None,
                     audio_hash: Optional[str] = None) -> Dict:
        """
        Classify a single audio node.
        
        Args:
            wav_path: Path to mono stem WAV
            node_id: Node ID (e.g., "11.1")
            stem_name: Optional stem filename for fallback
            mir_features: Optional MIR features for fallback
            audio_hash: Optional audio hash for caching
            
        Returns:
            Classification result dict with keys:
            - node_id: Node ID
            - category: Canonical category
            - category_confidence: Confidence score
            - role_hint: Role hint
            - role_confidence: Confidence score
            - top_labels: List of top raw labels from model
            - backend: Model version info
            - fallbacks_used: List of fallback methods used
            
        Per spec (classify_README.md):
        API contract for classification results.
        """
        # Check cache
        if audio_hash:
            cached = self.load_from_cache(audio_hash)
            if cached:
                print(f"    Loaded classification from cache: {node_id}")
                return cached
        
        result = {
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
        
        # Try Essentia models first
        try:
            # Instrument classification
            instrument_preds = self.run_essentia_instrument_classifier(wav_path)
            result["top_labels"] = instrument_preds[:5]  # Keep top 5
            
            category, cat_conf = self.map_instrument_to_category(instrument_preds)
            
            # Role classification
            role_probs = self.run_essentia_role_classifier(wav_path)
            role_hint, role_conf = self.map_role_to_hint(role_probs)
            
            # Check thresholds
            if cat_conf >= self.CATEGORY_THRESHOLD:
                result["category"] = category
                result["category_confidence"] = cat_conf
            
            if role_conf >= self.ROLE_THRESHOLD:
                result["role_hint"] = role_hint
                result["role_confidence"] = role_conf
        
        except Exception as e:
            print(f"    Essentia classification failed: {e}")
            result["fallbacks_used"].append("essentia_error")
        
        # Apply fallbacks if needed
        if result["category"] == "unknown" and stem_name:
            filename_result = self.apply_filename_fallback(stem_name)
            if filename_result:
                result["category"] = filename_result[0]
                result["role_hint"] = filename_result[1]
                result["fallbacks_used"].append("filename")
        
        if result["category"] == "unknown" and mir_features:
            mir_result = self.apply_mir_fallback(mir_features)
            if mir_result:
                result["category"] = mir_result[0]
                result["role_hint"] = mir_result[1]
                result["fallbacks_used"].append("mir")
        
        if not result["fallbacks_used"]:
            result["fallbacks_used"].append("none")
        
        # Cache result
        if audio_hash:
            self.save_to_cache(audio_hash, result)
        
        return result
    
    def classify_all_stems(self, manifest: Dict, mir_summary: Dict, 
                          wav_dir: str) -> Dict:
        """
        Classify all stems from manifest.
        
        Args:
            manifest: Session manifest
            mir_summary: MIR summary dict
            wav_dir: Directory containing normalized mono WAVs
            
        Returns:
            Classification results dict keyed by node_id
        """
        print("Stage 3: Classification + Role Assignment")
        
        results = {}
        stems = manifest["stems"]
        
        for i, stem in enumerate(stems):
            stem_name = stem["filename"]
            stem_hash = stem.get("hash", "")
            
            print(f"  Classifying stem {i+1}/{len(stems)}: {stem_name}")
            
            # Classify each node (multiple if stereo)
            for j, (group_id, wav_name) in enumerate(zip(stem["group_ids"], stem["wav_names"])):
                node_id = f"{group_id}.1"
                wav_path = Path(wav_dir) / wav_name
                
                # Get MIR features for this node
                mir_features = mir_summary["stems"].get(node_id, {}).get("features", {})
                
                result = self.classify_node(
                    wav_path=str(wav_path),
                    node_id=node_id,
                    stem_name=stem_name if j == 0 else f"{stem_name}_R",  # Differentiate L/R
                    mir_features=mir_features,
                    audio_hash=stem_hash,
                )
                
                results[node_id] = result
                print(f"    {node_id}: {result['category']} ({result['role_hint']})")
        
        return results
