"""
SpatialSeed Main Pipeline
==========================
Orchestrates all stages of the SpatialSeed authoring pipeline.

Per spec: lowLevelSpecsV1.md § 7, agents.md § 8
"""

import json
from pathlib import Path
from typing import Optional, Tuple

# Import all pipeline modules
from session import SessionManager
from audio_io import AudioNormalizer
from mir.extract import MIRExtractor
from mir.classify import InstrumentClassifier
from seed_matrix import SeedMatrix
from spf import SPFResolver
from placement import PlacementEngine
from gesture_engine import GestureEngine
from lusid_writer import LUSIDSceneWriter
from export.lusid_package import LUSIDPackageExporter
from export.adm_bw64 import ADMBw64Exporter


class SpatialSeedPipeline:
    """
    Main pipeline orchestrator for SpatialSeed.
    
    Executes all stages from stem discovery to final export.
    """
    
    def __init__(self, project_dir: str, stems_dir: str,
                 config: Optional[dict] = None):
        """
        Initialize pipeline.
        
        Args:
            project_dir: Root directory for project
            stems_dir: Directory containing input stems
            config: Optional configuration dict
        """
        self.project_dir = Path(project_dir)
        self.stems_dir = Path(stems_dir)
        self.config = config or {}
        
        # Create subdirectories
        self.work_dir = self.project_dir / "work"
        self.cache_dir = self.project_dir / "cache"
        self.export_dir = self.project_dir / "export"
        
        for dir_path in [self.work_dir, self.cache_dir, self.export_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def run(self, u: float = 0.5, v: float = 0.3,
           export_adm: bool = False) -> dict:
        """
        Run complete pipeline.
        
        Args:
            u: Seed Matrix u parameter (aesthetic variation)
            v: Seed Matrix v parameter (dynamic immersion)
            export_adm: If True, also export ADM/BW64
            
        Returns:
            Pipeline results dict
            
        Pipeline stages:
        0. Session + Discovery
        1. Normalize + Split Audio
        2. MIR Extraction
        3. Classification + Role Assignment
        4. Seed Matrix Selection
        5. SPF Resolution → StyleProfile
        6. Static Placement
        7. Gesture Generation (Sparse Keyframes)
        8. LUSID Scene Assembly
        9. Exports (LUSID Package + optional ADM/BW64)
        """
        print("=" * 60)
        print("SpatialSeed Pipeline v0.1.0")
        print("=" * 60)
        
        # Stage 0: Session + Discovery
        session = SessionManager(str(self.project_dir), str(self.stems_dir))
        manifest = session.run()
        
        # Stage 1: Normalize + Split Audio
        audio_normalizer = AudioNormalizer(cache_dir=str(self.cache_dir / "audio"))
        wav_dir = self.work_dir / "wavs"
        wav_dir.mkdir(exist_ok=True)
        audio_normalizer.process_all_stems(manifest, str(wav_dir))
        
        # Stage 2: MIR Extraction
        mir_extractor = MIRExtractor(cache_dir=str(self.cache_dir / "mir"))
        mir_summary = mir_extractor.extract_all_features(manifest)
        mir_summary_path = self.work_dir / "mir_summary.json"
        mir_extractor.save_mir_summary(mir_summary, str(mir_summary_path))
        
        # Stage 3: Classification + Role Assignment
        classifier = InstrumentClassifier(cache_dir=str(self.cache_dir / "classify"))
        classifications = classifier.classify_all_stems(manifest, mir_summary, str(wav_dir))
        
        # Stage 4: Seed Matrix Selection
        seed_matrix = SeedMatrix()
        style_vector = seed_matrix.map_uv_to_z(u, v)
        print(f"Stage 4: Seed Matrix Selection")
        print(f"  (u={u:.2f}, v={v:.2f}) → z={style_vector}")
        
        # Save selection
        selection_path = self.work_dir / "seed_selection.json"
        seed_matrix.save_selection(u, v, style_vector, str(selection_path))
        
        # Stage 5: SPF Resolution → StyleProfile
        spf_config_path = self.config.get("spf_config_path")
        spf_resolver = SPFResolver(spf_config_path=spf_config_path)
        profiles = spf_resolver.resolve_all_profiles(classifications, mir_summary, style_vector)
        
        # Save profiles
        profiles_path = self.work_dir / "style_profiles.json"
        spf_resolver.save_profiles(profiles, str(profiles_path))
        
        # Stage 6: Static Placement
        placement_engine = PlacementEngine()
        placements = placement_engine.compute_all_placements(profiles, style_vector, mir_summary)
        
        # Stage 7: Gesture Generation
        duration = 300.0  # TODO: Compute from longest stem
        gesture_engine = GestureEngine(duration_seconds=duration)
        keyframes = gesture_engine.generate_all_gestures(placements, profiles, mir_summary)
        
        # Print keyframe stats
        stats = gesture_engine.get_keyframe_stats()
        print(f"  Keyframe stats: {stats}")
        
        # Stage 8: LUSID Scene Assembly
        lusid_writer = LUSIDSceneWriter(sample_rate=48000)
        scene_path = self.work_dir / "scene.lusid.json"
        lusid_writer.write_scene(keyframes, str(scene_path))
        
        # Validate scene
        if lusid_writer.validate_scene():
            print("  LUSID scene validated ✓")
        
        # Stage 9: Exports
        print("=" * 60)
        print("Exports")
        print("=" * 60)
        
        # Export A: LUSID Package
        lusid_package_dir = self.export_dir / "lusid_package"
        lusid_exporter = LUSIDPackageExporter(str(lusid_package_dir))
        lusid_exporter.create_package(
            scene_path=str(scene_path),
            mir_summary_path=str(mir_summary_path),
            wav_dir=str(wav_dir),
            manifest=manifest,
        )
        
        # Validate package
        if lusid_exporter.validate_package():
            print("  LUSID package validated ✓")
        
        # Export B: ADM/BW64 (optional)
        if export_adm:
            lusid_submodule_path = self.project_dir.parent / "LUSID"
            adm_exporter = ADMBw64Exporter(str(lusid_submodule_path))
            
            adm_output_path = self.export_dir / "export.adm.wav"
            adm_exporter.export_adm_bw64(
                lusid_package_dir=str(lusid_package_dir),
                manifest=manifest,
                output_path=str(adm_output_path),
                sidecar_xml=True,
            )
            
            # Validate BW64
            if adm_exporter.validate_bw64(str(adm_output_path)):
                print("  ADM/BW64 validated ✓")
        
        print("=" * 60)
        print("Pipeline complete")
        print("=" * 60)
        print(f"LUSID package: {lusid_package_dir}")
        if export_adm:
            print(f"ADM/BW64: {adm_output_path}")
        
        return {
            "manifest": manifest,
            "style_vector": style_vector.tolist(),
            "lusid_package": str(lusid_package_dir),
            "keyframe_stats": stats,
        }


def main():
    """
    Command-line entry point.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="SpatialSeed: Immersive Spatial Scene Authoring")
    parser.add_argument("stems_dir", help="Directory containing input stems")
    parser.add_argument("--project-dir", default=".", help="Project directory (default: current dir)")
    parser.add_argument("-u", type=float, default=0.5, 
                       help="Seed Matrix u (aesthetic variation, 0-1)")
    parser.add_argument("-v", type=float, default=0.3,
                       help="Seed Matrix v (dynamic immersion, 0-1)")
    parser.add_argument("--export-adm", action="store_true",
                       help="Also export ADM/BW64")
    parser.add_argument("--config", help="Path to configuration JSON")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Run pipeline
    pipeline = SpatialSeedPipeline(
        project_dir=args.project_dir,
        stems_dir=args.stems_dir,
        config=config,
    )
    
    results = pipeline.run(u=args.u, v=args.v, export_adm=args.export_adm)
    
    # Save results
    results_path = Path(args.project_dir) / "export" / "results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
