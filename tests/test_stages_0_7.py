#!/usr/bin/env python3
"""
SpatialSeed -- smoke test for stages 0-7 with real stems.

Usage (from repo root, with venv activated):
    python tests/test_stages_0_7.py

Expects real WAV stems in  test_session/stems/
Writes working files into   test_session/work/  and  test_session/cache/

Stages tested:
0. Session / Discovery
1. Audio Normalisation (96 kHz -> 48 kHz, stereo split)
2. MIR Feature Extraction (librosa)
3. Classification (filename + MIR heuristics)
4. Seed Matrix Selection
5. SPF Resolution -> StyleProfile
6. Static Placement
7. Gesture Generation (sparse keyframes)
"""

import json
import sys
import shutil
import time
from pathlib import Path

# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.session import SessionManager
from src.audio_io import AudioNormalizer
from src.mir.extract import MIRExtractor
from src.mir.classify import InstrumentClassifier
from src.seed_matrix import SeedMatrix
from src.spf import SPFResolver
from src.placement import PlacementEngine
from src.gesture_engine import GestureEngine

# ---------------------------------------------------------------------------
STEMS_DIR = REPO_ROOT / "test_session" / "stems"
PROJECT_DIR = REPO_ROOT / "test_session"
WAV_DIR = PROJECT_DIR / "work" / "wavs"
CACHE_DIR = PROJECT_DIR / "cache"


def check_stems():
    wavs = list(STEMS_DIR.glob("*.wav"))
    aifs = list(STEMS_DIR.glob("*.aif")) + list(STEMS_DIR.glob("*.aiff"))
    flacs = list(STEMS_DIR.glob("*.flac"))
    all_stems = wavs + aifs + flacs
    if not all_stems:
        print(f"ERROR: No audio stems in {STEMS_DIR}")
        sys.exit(1)
    print(f"Found {len(all_stems)} stems in {STEMS_DIR}")
    for s in sorted(all_stems):
        print(f"  - {s.name}")


# === Stage runners ========================================================

def run_stage_0():
    print("\n" + "=" * 60)
    print("STAGE 0 -- Session / Discovery")
    print("=" * 60)
    t0 = time.perf_counter()
    session = SessionManager(str(PROJECT_DIR), str(STEMS_DIR))
    manifest = session.run()
    assert len(manifest["stems"]) > 0
    assert manifest["sample_rate"] == 48000
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {manifest['stem_count']} stems, {manifest['object_count']} objects  ({dt:.1f}s)")
    return manifest


def run_stage_1(manifest):
    print("\n" + "=" * 60)
    print("STAGE 1 -- Audio Normalisation")
    print("=" * 60)
    t0 = time.perf_counter()
    normalizer = AudioNormalizer(cache_dir=str(CACHE_DIR / "audio"))
    normalizer.process_all_stems(manifest, str(WAV_DIR))
    import soundfile as sf
    wav_files = sorted(WAV_DIR.glob("*.wav"))
    assert len(wav_files) > 0
    for wf in wav_files:
        info = sf.info(str(wf))
        assert info.samplerate == 48000, f"{wf.name} sr={info.samplerate}"
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {len(wav_files)} WAVs at 48 kHz  ({dt:.1f}s)")


def run_stage_2(manifest):
    print("\n" + "=" * 60)
    print("STAGE 2 -- MIR Feature Extraction")
    print("=" * 60)
    t0 = time.perf_counter()
    extractor = MIRExtractor(cache_dir=str(CACHE_DIR / "mir"))
    mir_summary = extractor.extract_all_features(manifest)
    mir_path = PROJECT_DIR / "work" / "mir_summary.json"
    extractor.save_mir_summary(mir_summary, str(mir_path))
    assert len(mir_summary["stems"]) > 0
    dt = time.perf_counter() - t0
    print(f"\n  [OK] MIR features for {len(mir_summary['stems'])} nodes  ({dt:.1f}s)")
    return mir_summary


def run_stage_3(manifest, mir_summary):
    print("\n" + "=" * 60)
    print("STAGE 3 -- Classification")
    print("=" * 60)
    t0 = time.perf_counter()
    classifier = InstrumentClassifier(cache_dir=str(CACHE_DIR / "classify"))
    classifications = classifier.classify_all_stems(manifest, mir_summary, str(WAV_DIR))
    assert len(classifications) > 0
    for nid, res in classifications.items():
        assert res["category"] != "", f"Empty category for {nid}"
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {len(classifications)} nodes classified  ({dt:.1f}s)")
    return classifications


def run_stage_4(u=0.5, v=0.3):
    print("\n" + "=" * 60)
    print("STAGE 4 -- Seed Matrix Selection")
    print("=" * 60)
    sm = SeedMatrix()
    z = sm.map_uv_to_z(u, v)
    desc = sm.describe_z(z)
    print(f"  (u={u}, v={v})")
    for k, val in desc.items():
        print(f"    {k}: {val}")
    assert z.shape == (8,)
    print(f"\n  [OK] z = {z}")
    return z


def run_stage_5(manifest, classifications, mir_summary, z):
    print("\n" + "=" * 60)
    print("STAGE 5 -- SPF Resolution")
    print("=" * 60)
    t0 = time.perf_counter()
    spf = SPFResolver()
    profiles = spf.resolve_all_profiles(manifest, classifications, mir_summary, z)
    assert len(profiles) > 0
    for nid, sp in profiles.items():
        assert -1.0 <= sp.base_x <= 1.0, f"{nid} x out of cube"
        assert -1.0 <= sp.base_y <= 1.0, f"{nid} y out of cube"
        assert -1.0 <= sp.base_z <= 1.0, f"{nid} z out of cube"
    profiles_path = PROJECT_DIR / "work" / "style_profiles.json"
    spf.save_profiles(profiles, str(profiles_path))
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {len(profiles)} style profiles resolved  ({dt:.1f}s)")
    return profiles


def run_stage_6(profiles, z):
    print("\n" + "=" * 60)
    print("STAGE 6 -- Static Placement")
    print("=" * 60)
    t0 = time.perf_counter()
    engine = PlacementEngine()
    placements = engine.compute_all_placements(profiles, z)
    assert len(placements) > 0
    for nid, (x, y, zp) in placements.items():
        assert -1.0 <= x <= 1.0, f"{nid} x={x} out of cube"
        assert -1.0 <= y <= 1.0, f"{nid} y={y} out of cube"
        assert -1.0 <= zp <= 1.0, f"{nid} z={zp} out of cube"
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {len(placements)} placements  ({dt:.1f}s)")
    return placements


def run_stage_7(placements, profiles, mir_summary, duration):
    print("\n" + "=" * 60)
    print("STAGE 7 -- Gesture Generation")
    print("=" * 60)
    t0 = time.perf_counter()
    engine = GestureEngine(duration_seconds=duration)
    keyframes = engine.generate_all_gestures(placements, profiles, mir_summary)
    stats = engine.get_keyframe_stats()
    assert stats["total_objects"] > 0
    # Verify every node has a t=0 keyframe
    for nid, kfs in keyframes.items():
        assert len(kfs) >= 1, f"{nid} has no keyframes"
        assert kfs[0].time == 0.0, f"{nid} first keyframe at t={kfs[0].time}, expected 0.0"
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {stats['total_keyframes']} keyframes across {stats['total_objects']} objects  ({dt:.1f}s)")
    print(f"    static: {stats['static_objects']}  animated: {stats['animated_objects']}  avg: {stats['avg_keyframes_per_object']}")
    return keyframes, stats


# === Summary ==============================================================

def print_summary(manifest, classifications, profiles, placements, keyframes, stats):
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    for stem in manifest["stems"]:
        short = stem["filename"].split("NO BVs ")[-1] if "NO BVs " in stem["filename"] else stem["filename"]
        print(f"\n  Stem: {short}")
        for nid in stem["node_ids"]:
            cls = classifications.get(nid, {})
            sp = profiles.get(nid)
            pos = placements.get(nid, (0, 0, 0))
            n_kf = len(keyframes.get(nid, []))
            cat = cls.get("category", "?")
            role = cls.get("role_hint", "?")
            motion = sp.motion_type if sp else "?"
            print(f"    {nid}: {cat}/{role}  pos=({pos[0]:.3f},{pos[1]:.3f},{pos[2]:.3f})  motion={motion}  kf={n_kf}")

    print(f"\n  Keyframe totals: {stats['total_keyframes']} kf, "
          f"{stats['static_objects']} static, {stats['animated_objects']} animated")

    print("\n" + "=" * 60)
    print("All stages 0-7 passed.")
    print("=" * 60)


# === Main =================================================================

def main():
    t_total = time.perf_counter()

    # Clean work/cache but keep stems
    for sub in ["work", "cache"]:
        d = PROJECT_DIR / sub
        if d.exists():
            shutil.rmtree(d)

    check_stems()

    manifest = run_stage_0()
    run_stage_1(manifest)
    mir_summary = run_stage_2(manifest)
    classifications = run_stage_3(manifest, mir_summary)

    # Seed Matrix: moderate settings
    z = run_stage_4(u=0.5, v=0.3)

    profiles = run_stage_5(manifest, classifications, mir_summary, z)
    placements = run_stage_6(profiles, z)

    duration = manifest.get("max_duration_seconds", 300.0)
    keyframes, stats = run_stage_7(placements, profiles, mir_summary, duration)

    # Save classifications for downstream stages
    cls_path = PROJECT_DIR / "work" / "classifications.json"
    cls_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cls_path, "w") as f:
        json.dump(classifications, f, indent=2)

    print_summary(manifest, classifications, profiles, placements, keyframes, stats)
    print(f"\nTotal elapsed: {time.perf_counter() - t_total:.1f}s")


if __name__ == "__main__":
    main()
