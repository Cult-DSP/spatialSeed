#!/usr/bin/env python3
"""
SpatialSeed -- full pipeline smoke test for stages 0-9A with real stems.

Usage (from repo root, with venv activated):
    python tests/test_stages_0_9.py

Expects real WAV stems in  test_session/stems/
Writes working files into   test_session/work/  and  test_session/cache/
LUSID package into          test_session/export/lusid_package/

Stages tested:
0. Session / Discovery
1. Audio Normalisation (96 kHz -> 48 kHz, stereo split)
2. MIR Feature Extraction (librosa)
3. Classification (filename + MIR heuristics)
4. Seed Matrix Selection
5. SPF Resolution -> StyleProfile
6. Static Placement
7. Gesture Generation (sparse keyframes)
8. LUSID Scene Assembly (scene.lusid.json)
9A. LUSID Package Export (containsAudio.json, WAV copy, validation)
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
from src.lusid_writer import LUSIDSceneWriter
from src.export.lusid_package import LUSIDPackageExporter
from src.export.adm_bw64 import ADMBw64Exporter

# ---------------------------------------------------------------------------
STEMS_DIR = REPO_ROOT / "test_session" / "stems"
PROJECT_DIR = REPO_ROOT / "test_session"
WAV_DIR = PROJECT_DIR / "work" / "wavs"
CACHE_DIR = PROJECT_DIR / "cache"
EXPORT_DIR = PROJECT_DIR / "export"


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
    for nid, kfs in keyframes.items():
        assert len(kfs) >= 1, f"{nid} has no keyframes"
        assert kfs[0].time == 0.0, f"{nid} first keyframe at t={kfs[0].time}, expected 0.0"
    dt = time.perf_counter() - t0
    print(f"\n  [OK] {stats['total_keyframes']} keyframes across {stats['total_objects']} objects  ({dt:.1f}s)")
    print(f"    static: {stats['static_objects']}  animated: {stats['animated_objects']}  avg: {stats['avg_keyframes_per_object']}")
    return keyframes, stats


def run_stage_8(keyframes):
    print("\n" + "=" * 60)
    print("STAGE 8 -- LUSID Scene Assembly")
    print("=" * 60)
    t0 = time.perf_counter()

    writer = LUSIDSceneWriter(sample_rate=48000)
    scene_path = PROJECT_DIR / "work" / "scene.lusid.json"
    scene = writer.write_scene(keyframes, str(scene_path))

    # Validate
    errors = writer.validate_scene(scene)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        assert False, f"Scene validation failed: {errors}"

    # Structural checks
    frames = scene["frames"]
    assert len(frames) > 0, "No frames in scene"
    assert frames[0]["time"] == 0.0, "First frame not at t=0"
    assert scene["version"] == "0.5"
    assert scene["sampleRate"] == 48000

    # Count node types at t=0
    t0_nodes = frames[0]["nodes"]
    types = [n["type"] for n in t0_nodes]
    n_ds = types.count("direct_speaker")
    n_lfe = types.count("LFE")
    n_ao = types.count("audio_object")
    print(f"  t=0 frame: {n_ds} direct_speaker, {n_lfe} LFE, {n_ao} audio_object")

    assert n_ds == 9, f"Expected 9 direct_speaker nodes at t=0, got {n_ds}"
    assert n_lfe == 1, f"Expected 1 LFE node at t=0, got {n_lfe}"
    assert n_ao > 0, f"No audio_object nodes at t=0"

    # Check all audio_object carts are in [-1,1] range
    for f in frames:
        for n in f["nodes"]:
            if n["type"] == "audio_object":
                for i, c in enumerate(n["cart"]):
                    assert -1.0 <= c <= 1.0, (
                        f"Node {n['id']} t={f['time']} cart[{i}]={c} out of range"
                    )

    dt = time.perf_counter() - t0
    print(f"\n  [OK] {len(frames)} frames, scene validated  ({dt:.1f}s)")
    return scene


def run_stage_9a(manifest):
    print("\n" + "=" * 60)
    print("STAGE 9A -- LUSID Package Export")
    print("=" * 60)
    t0 = time.perf_counter()

    pkg_dir = EXPORT_DIR / "lusid_package"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    exporter = LUSIDPackageExporter(str(pkg_dir))
    scene_path = PROJECT_DIR / "work" / "scene.lusid.json"
    mir_path = PROJECT_DIR / "work" / "mir_summary.json"
    contains = exporter.create_package(
        scene_path=str(scene_path),
        mir_summary_path=str(mir_path),
        wav_dir=str(WAV_DIR),
        manifest=manifest,
    )

    # Validate
    errors = exporter.validate_package()
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        assert False, f"Package validation failed: {errors}"

    # Verify key files exist
    assert (pkg_dir / "scene.lusid.json").exists(), "Missing scene.lusid.json"
    assert (pkg_dir / "containsAudio.json").exists(), "Missing containsAudio.json"
    assert (pkg_dir / "mir_summary.json").exists(), "Missing mir_summary.json"
    assert (pkg_dir / "LFE.wav").exists(), "Missing LFE.wav"

    # Verify containsAudio content
    channels = contains["channels"]
    n_audio = sum(1 for c in channels if c["contains_audio"])
    n_silent = sum(1 for c in channels if not c["contains_audio"])
    print(f"  containsAudio: {n_audio} active, {n_silent} silent, {len(channels)} total")

    # Beds should all be silent (they are zeros in v1)
    bed_channels = channels[:10]  # first 10 are beds
    for bc in bed_channels:
        assert not bc["contains_audio"], (
            f"Bed channel {bc['node_id']} should be silent, rms={bc['rms_db']}"
        )

    # Objects should all contain audio
    obj_channels = channels[10:]
    for oc in obj_channels:
        assert oc["contains_audio"], (
            f"Object channel {oc['node_id']} should contain audio, rms={oc['rms_db']}"
        )

    # Check WAV count in package
    pkg_wavs = list(pkg_dir.glob("*.wav"))
    print(f"  {len(pkg_wavs)} WAV files in package")

    dt = time.perf_counter() - t0
    print(f"\n  [OK] LUSID package validated at {pkg_dir}  ({dt:.1f}s)")
    return contains


def run_stage_9b(manifest):
    print("\n" + "=" * 60)
    print("STAGE 9B -- ADM/BW64 Export")
    print("=" * 60)
    t0 = time.perf_counter()

    pkg_dir = EXPORT_DIR / "lusid_package"
    adm_path = EXPORT_DIR / "export.adm.wav"
    xml_path = EXPORT_DIR / "export.adm.xml"

    exporter = ADMBw64Exporter()
    result = exporter.export_adm_bw64(
        lusid_package_dir=str(pkg_dir),
        manifest=manifest,
        output_path=str(adm_path),
        sidecar_xml=True,
    )

    # Validate
    errors = exporter.validate_bw64(str(adm_path))
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        assert False, f"ADM validation failed: {errors}"

    assert adm_path.exists(), "ADM WAV not created"
    assert xml_path.exists(), "Sidecar XML not created"

    # Check channel count
    import soundfile as sf_check
    info = sf_check.info(str(adm_path))
    expected_ch = 10 + manifest["object_count"]
    assert info.channels == expected_ch, (
        f"ADM has {info.channels} channels, expected {expected_ch}"
    )
    assert info.samplerate == 48000

    # Check ADM XML is well-formed
    import xml.etree.ElementTree as ET_check
    tree = ET_check.parse(str(xml_path))
    root = tree.getroot()
    assert "ebuCoreMain" in root.tag, f"Unexpected XML root: {root.tag}"

    dt = time.perf_counter() - t0
    print(f"\n  [OK] ADM export: {result['channels']} ch, "
          f"{result['duration_seconds']}s, {result['size_mb']} MB  ({dt:.1f}s)")
    return result


# === Summary ==============================================================

def print_summary(manifest, classifications, profiles, placements, keyframes,
                  stats, scene, contains, adm_result):
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

    print(f"\n  Keyframes: {stats['total_keyframes']} total, "
          f"{stats['static_objects']} static, {stats['animated_objects']} animated")
    print(f"  Scene: {len(scene['frames'])} frames, version {scene['version']}")
    print(f"  Package: {contains['total_channels']} channels, "
          f"{sum(1 for c in contains['channels'] if c['contains_audio'])} active")
    print(f"  ADM: {adm_result['channels']} ch, {adm_result['duration_seconds']}s, "
          f"{adm_result['size_mb']} MB")

    print("\n" + "=" * 60)
    print("All stages 0-9 passed.")
    print("=" * 60)


# === Main =================================================================

def main():
    t_total = time.perf_counter()

    # Clean work/cache/export but keep stems
    for sub in ["work", "cache", "export"]:
        d = PROJECT_DIR / sub
        if d.exists():
            shutil.rmtree(d)

    check_stems()

    # Stages 0-3: discovery, audio, MIR, classification
    manifest = run_stage_0()
    run_stage_1(manifest)
    mir_summary = run_stage_2(manifest)
    classifications = run_stage_3(manifest, mir_summary)

    # Stage 4: seed matrix
    z = run_stage_4(u=0.5, v=0.3)

    # Stages 5-7: spatial processing
    profiles = run_stage_5(manifest, classifications, mir_summary, z)
    placements = run_stage_6(profiles, z)
    duration = manifest.get("max_duration_seconds", 300.0)
    keyframes, stats = run_stage_7(placements, profiles, mir_summary, duration)

    # Stage 8: LUSID scene
    scene = run_stage_8(keyframes)

    # Stage 9A: LUSID package
    contains = run_stage_9a(manifest)

    # Stage 9B: ADM export
    adm_result = run_stage_9b(manifest)

    # Summary
    print_summary(manifest, classifications, profiles, placements,
                  keyframes, stats, scene, contains, adm_result)
    print(f"\nTotal elapsed: {time.perf_counter() - t_total:.1f}s")


if __name__ == "__main__":
    main()
