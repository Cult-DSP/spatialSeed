#!/usr/bin/env python3
"""
SpatialSeed -- smoke test for stages 0-3 using real stems.

Usage (from repo root, with venv activated):
    python tests/test_stages_0_3.py

Expects real WAV stems in  test_session/stems/
The script will write working files into  test_session/work/  and  test_session/cache/

This script:
1. Runs Stage 0 (session / discovery)
2. Runs Stage 1 (audio normalisation  -- 96 kHz -> 48 kHz, stereo split)
3. Runs Stage 2 (MIR feature extraction via librosa)
4. Runs Stage 3 (classification via filename + MIR heuristics)
5. Prints summary and basic assertions
"""

import json
import sys
import shutil
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path (mirrors what activate.sh does)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.session import SessionManager
from src.audio_io import AudioNormalizer
from src.mir.extract import MIRExtractor
from src.mir.classify import InstrumentClassifier

# ---------------------------------------------------------------------------
# Paths -- uses the real test_session directory
# ---------------------------------------------------------------------------
STEMS_DIR = REPO_ROOT / "test_session" / "stems"
PROJECT_DIR = REPO_ROOT / "test_session"
WAV_DIR = PROJECT_DIR / "work" / "wavs"
CACHE_DIR = PROJECT_DIR / "cache"


def check_stems() -> None:
    """Abort early if no stems are present."""
    wavs = list(STEMS_DIR.glob("*.wav"))
    aifs = list(STEMS_DIR.glob("*.aif")) + list(STEMS_DIR.glob("*.aiff"))
    flacs = list(STEMS_DIR.glob("*.flac"))
    all_stems = wavs + aifs + flacs
    if not all_stems:
        print(f"ERROR: No audio stems found in {STEMS_DIR}")
        print("Place WAV / AIF / FLAC stems there and re-run.")
        sys.exit(1)
    print(f"Found {len(all_stems)} stems in {STEMS_DIR}")
    for s in sorted(all_stems):
        print(f"  - {s.name}")


# ===================================================================
# Stage runners
# ===================================================================

def run_stage_0() -> dict:
    """Stage 0: Session + Discovery."""
    print("\n" + "=" * 60)
    print("STAGE 0 -- Session / Discovery")
    print("=" * 60)
    t0 = time.perf_counter()

    session = SessionManager(str(PROJECT_DIR), str(STEMS_DIR))
    manifest = session.run()

    # Basic checks
    assert len(manifest["stems"]) > 0, "No stems discovered"
    assert manifest["sample_rate"] == 48000
    for stem in manifest["stems"]:
        assert "hash" in stem, f"Missing hash for {stem['filename']}"
        assert "group_ids" in stem, f"Missing group_ids for {stem['filename']}"

    elapsed = time.perf_counter() - t0
    print(f"\n  [OK] Manifest: {manifest['stem_count']} stems, "
          f"{manifest['object_count']} objects  ({elapsed:.1f}s)")
    return manifest


def run_stage_1(manifest: dict) -> None:
    """Stage 1: Normalize + Split Audio (96 kHz stereo -> 48 kHz mono)."""
    print("\n" + "=" * 60)
    print("STAGE 1 -- Audio Normalisation")
    print("=" * 60)
    t0 = time.perf_counter()

    normalizer = AudioNormalizer(cache_dir=str(CACHE_DIR / "audio"))
    normalizer.process_all_stems(manifest, str(WAV_DIR))

    # Check that WAVs were written
    import soundfile as sf
    wav_files = sorted(WAV_DIR.glob("*.wav"))
    assert len(wav_files) > 0, "No WAV files produced"

    # Check sample rates and mono
    for wf in wav_files:
        info = sf.info(str(wf))
        assert info.samplerate == 48000, (
            f"{wf.name} has sr={info.samplerate}, expected 48000"
        )
        if not wf.name.startswith("bed_") and wf.name != "LFE.wav":
            assert info.channels == 1, (
                f"{wf.name} has {info.channels} ch, expected 1 (mono)"
            )

    elapsed = time.perf_counter() - t0
    print(f"\n  [OK] {len(wav_files)} WAVs at 48 kHz in {WAV_DIR}  ({elapsed:.1f}s)")


def run_stage_2(manifest: dict) -> dict:
    """Stage 2: MIR Feature Extraction (librosa)."""
    print("\n" + "=" * 60)
    print("STAGE 2 -- MIR Feature Extraction")
    print("=" * 60)
    t0 = time.perf_counter()

    extractor = MIRExtractor(cache_dir=str(CACHE_DIR / "mir"))
    mir_summary = extractor.extract_all_features(manifest)

    # Save
    mir_path = PROJECT_DIR / "work" / "mir_summary.json"
    extractor.save_mir_summary(mir_summary, str(mir_path))

    # Checks
    assert len(mir_summary["stems"]) > 0, "No MIR features extracted"
    for node_id, entry in mir_summary["stems"].items():
        feats = entry["features"]
        assert "spectral_centroid_mean" in feats, f"Missing centroid for {node_id}"
        assert "onset_density" in feats, f"Missing onset_density for {node_id}"

    elapsed = time.perf_counter() - t0
    print(f"\n  [OK] MIR features for {len(mir_summary['stems'])} nodes  "
          f"({elapsed:.1f}s)")
    return mir_summary


def run_stage_3(manifest: dict, mir_summary: dict) -> dict:
    """Stage 3: Classification + Role Assignment."""
    print("\n" + "=" * 60)
    print("STAGE 3 -- Classification")
    print("=" * 60)
    t0 = time.perf_counter()

    classifier = InstrumentClassifier(cache_dir=str(CACHE_DIR / "classify"))
    classifications = classifier.classify_all_stems(
        manifest, mir_summary, str(WAV_DIR)
    )

    # Checks
    assert len(classifications) > 0, "No classifications produced"
    for node_id, result in classifications.items():
        assert result["category"] != "", f"Empty category for {node_id}"
        assert "fallbacks_used" in result

    elapsed = time.perf_counter() - t0
    print(f"\n  [OK] Classified {len(classifications)} nodes  ({elapsed:.1f}s)")
    return classifications


# ===================================================================
# Summary
# ===================================================================

def print_summary(manifest, mir_summary, classifications):
    """Print a human-readable summary of the test run."""
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    for stem in manifest["stems"]:
        print(f"\n  Stem: {stem['filename']}")
        print(f"    channels={stem['channels']}  "
              f"node_ids={stem['node_ids']}  "
              f"group_ids={stem['group_ids']}")

        for node_id in stem["node_ids"]:
            cls = classifications.get(node_id, {})
            mir = mir_summary["stems"].get(node_id, {}).get("features", {})
            centroid = mir.get("spectral_centroid_mean", "?")
            onset = mir.get("onset_density", "?")
            harm = mir.get("harmonic_ratio", "?")
            if isinstance(centroid, float):
                centroid = f"{centroid:.1f}"
            if isinstance(onset, float):
                onset = f"{onset:.2f}"
            if isinstance(harm, float):
                harm = f"{harm:.3f}"
            print(f"    {node_id}:")
            print(f"      category   = {cls.get('category', '?')}")
            print(f"      role_hint  = {cls.get('role_hint', '?')}")
            print(f"      fallbacks  = {cls.get('fallbacks_used', [])}")
            print(f"      centroid   = {centroid} Hz")
            print(f"      onsets     = {onset} /s")
            print(f"      harm_ratio = {harm}")

    # Save classifications to disk for later stages
    cls_path = PROJECT_DIR / "work" / "classifications.json"
    cls_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cls_path, "w") as f:
        json.dump(classifications, f, indent=2)
    print(f"\n  Classifications saved to {cls_path}")

    print("\n" + "=" * 60)
    print("All stages 0-3 passed.")
    print("=" * 60)


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    t_total = time.perf_counter()

    # Clean previous working outputs but keep stems intact
    for sub in ["work", "cache"]:
        d = PROJECT_DIR / sub
        if d.exists():
            shutil.rmtree(d)

    check_stems()

    manifest = run_stage_0()
    run_stage_1(manifest)
    mir_summary = run_stage_2(manifest)
    classifications = run_stage_3(manifest, mir_summary)

    print_summary(manifest, mir_summary, classifications)

    elapsed = time.perf_counter() - t_total
    print(f"\nTotal elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
