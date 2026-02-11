"""
SpatialSeed Session Manager
============================
Stage 0: Session + Discovery

Responsibilities:
- Discover stems and reference mix from input directory
- Validate audio formats
- Build deterministic session manifest
- Sort stems lexicographically for deterministic ID allocation

Per spec: lowLevelSpecsV1.md § 7, agents.md § 8
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import json


class SessionManager:
    """
    Manages a SpatialSeed authoring session.
    
    Discovers audio files, validates formats, and creates a deterministic
    session manifest for downstream processing.
    """
    
    def __init__(self, project_dir: str, stems_dir: str):
        """
        Initialize session manager.
        
        Args:
            project_dir: Root directory for the SpatialSeed project
            stems_dir: Directory containing input stem WAV files
        """
        self.project_dir = Path(project_dir)
        self.stems_dir = Path(stems_dir)
        self.manifest = {}
        
    def discover_stems(self) -> List[Dict]:
        """
        Discover all WAV files in stems_dir.
        
        Returns:
            List of stem info dicts, sorted lexicographically by filename
            
        Per spec (agents.md § 7.1):
        - Sort input stem filenames lexicographically
        - Ensures deterministic ID allocation
        """
        # TODO: Scan stems_dir for .wav files
        # TODO: Sort lexicographically by filename
        # TODO: For each stem, gather:
        #   - filename
        #   - absolute path
        #   - file hash (for caching)
        #   - basic metadata (sample rate, channels, duration)
        # TODO: Log discovered stems
        
        stems = []
        # ...implementation...
        return stems
    
    def validate_audio_formats(self, stems: List[Dict]) -> bool:
        """
        Validate that all stems are readable WAV files.
        
        Args:
            stems: List of stem info dicts from discover_stems()
            
        Returns:
            True if all stems are valid, False otherwise
            
        Per spec (agents.md § 2.1):
        - All audio will be resampled to 48 kHz in the next stage
        - Accept any valid WAV format for now
        """
        # TODO: For each stem:
        #   - Check that file exists and is readable
        #   - Verify it's a valid WAV file
        #   - Log any format issues
        # TODO: Return False if any validation fails
        
        return True
    
    def allocate_object_ids(self, stems: List[Dict]) -> List[Dict]:
        """
        Allocate object group IDs starting from 11.
        
        Args:
            stems: List of stem info dicts (must be sorted)
            
        Returns:
            Updated stems list with allocated group IDs
            
        Per spec (agents.md § 7.1, 7.2):
        - Object groups start at 11
        - Stereo stems consume TWO groups (L then R)
        - Node X.1 maps to file X.1.wav
        - LFE special case: 4.1 → LFE.wav
        """
        # TODO: Iterate through sorted stems
        # TODO: For mono stems: allocate single group ID
        # TODO: For stereo stems: allocate TWO consecutive group IDs
        #   - first group = left channel
        #   - second group = right channel
        # TODO: Store mapping: stem → group_ids → wav_filenames
        # TODO: Log allocation table for diagnostics
        
        next_group_id = 11
        for stem in stems:
            channels = stem.get("channels", 1)
            if channels == 1:
                # Mono stem
                stem["group_ids"] = [next_group_id]
                stem["wav_names"] = [f"{next_group_id}.1.wav"]
                next_group_id += 1
            elif channels == 2:
                # Stereo stem: allocate two groups
                stem["group_ids"] = [next_group_id, next_group_id + 1]
                stem["wav_names"] = [f"{next_group_id}.1.wav", f"{next_group_id + 1}.1.wav"]
                next_group_id += 2
            else:
                # Unsupported channel count
                raise ValueError(f"Unsupported channel count {channels} for stem {stem['filename']}")
                
        return stems
    
    def create_manifest(self, stems: List[Dict]) -> Dict:
        """
        Create session manifest for reproducibility.
        
        Args:
            stems: List of stem info dicts with allocated IDs
            
        Returns:
            Session manifest dict
            
        Manifest includes:
        - Session metadata (timestamp, version)
        - Stem list with IDs and file mappings
        - Configuration snapshot
        """
        # TODO: Build manifest dict with:
        #   - version: SpatialSeed version
        #   - timestamp: creation time
        #   - sample_rate: 48000 (target)
        #   - stems: full stem list with IDs
        #   - config: snapshot of relevant config
        
        manifest = {
            "version": "0.1.0",
            "sample_rate": 48000,
            "stems": stems,
            # ...
        }
        
        return manifest
    
    def save_manifest(self, manifest: Dict, output_path: Optional[str] = None):
        """
        Save session manifest to disk.
        
        Args:
            manifest: Session manifest dict
            output_path: Optional custom path (defaults to project_dir/manifest.json)
        """
        if output_path is None:
            output_path = self.project_dir / "manifest.json"
        
        # TODO: Write manifest as formatted JSON
        # TODO: Log save location
        pass
    
    def run(self) -> Dict:
        """
        Execute full session discovery and validation.
        
        Returns:
            Session manifest dict
            
        Pipeline:
        1. Discover stems
        2. Validate formats
        3. Allocate object IDs
        4. Create manifest
        5. Save manifest
        """
        print("Stage 0: Session + Discovery")
        
        # Discover
        stems = self.discover_stems()
        print(f"  Discovered {len(stems)} stems")
        
        # Validate
        if not self.validate_audio_formats(stems):
            raise RuntimeError("Audio format validation failed")
        print("  All stems validated")
        
        # Allocate IDs
        stems = self.allocate_object_ids(stems)
        print("  Object IDs allocated")
        
        # Create manifest
        manifest = self.create_manifest(stems)
        
        # Save
        self.save_manifest(manifest)
        print("  Session manifest saved")
        
        return manifest


def compute_audio_hash(filepath: str) -> str:
    """
    Compute SHA256 hash of audio file for caching.
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Hex digest of file hash
    """
    # TODO: Read file in chunks
    # TODO: Compute SHA256 hash
    # TODO: Return hex digest
    hasher = hashlib.sha256()
    # ...implementation...
    return hasher.hexdigest()
