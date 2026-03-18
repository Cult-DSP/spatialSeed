"""
SpatialSeed Session Manager
============================
Stage 0: Session + Discovery

Responsibilities:
- Discover stems and reference mix from input directory
- Validate audio formats
- Build deterministic session manifest
- Sort stems lexicographically for deterministic ID allocation

Per spec: lowLevelSpecsV1.md 7, agents.md 8
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

import soundfile as sf

logger = logging.getLogger("spatialSeed.session")

# Supported audio extensions (case-insensitive)
SUPPORTED_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac"}


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
        self.manifest: Dict = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_stems(self) -> List[Dict]:
        """
        Discover all audio files in stems_dir.

        Returns:
            List of stem info dicts, sorted lexicographically by filename

        Per spec (agents.md 7.1):
        - Sort input stem filenames lexicographically
        - Ensures deterministic ID allocation
        """
        if not self.stems_dir.is_dir():
            raise FileNotFoundError(
                f"Stems directory does not exist: {self.stems_dir}"
            )

        stems: List[Dict] = []
        for entry in sorted(self.stems_dir.iterdir()):
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # Read audio metadata via soundfile (fast, header-only)
            try:
                info = sf.info(str(entry))
            except Exception as exc:
                logger.warning("Skipping unreadable file %s: %s", entry.name, exc)
                continue

            file_hash = compute_audio_hash(str(entry))

            stem = {
                "filename": entry.name,
                "path": str(entry.resolve()),
                "hash": file_hash,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "frames": info.frames,
                "duration_seconds": info.duration,
                "format": info.format,
                "subtype": info.subtype,
            }
            stems.append(stem)
            logger.info(
                "Discovered stem: %s  sr=%d  ch=%d  dur=%.2fs  hash=%s",
                entry.name,
                info.samplerate,
                info.channels,
                info.duration,
                file_hash[:12],
            )

        if not stems:
            raise RuntimeError(
                f"No supported audio files found in {self.stems_dir}"
            )

        return stems

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_audio_formats(self, stems: List[Dict]) -> bool:
        """
        Validate that all stems are readable audio files.

        Args:
            stems: List of stem info dicts from discover_stems()

        Returns:
            True if all stems are valid, False otherwise

        Per spec (agents.md 2.1):
        - All audio will be resampled to 48 kHz in the next stage
        - Accept any valid audio format for now
        """
        all_valid = True
        for stem in stems:
            p = Path(stem["path"])
            if not p.exists():
                logger.error("Stem file missing: %s", stem["path"])
                all_valid = False
                continue
            if stem["channels"] < 1 or stem["channels"] > 2:
                logger.error(
                    "Unsupported channel count %d for %s (must be 1 or 2)",
                    stem["channels"],
                    stem["filename"],
                )
                all_valid = False
                continue
            if stem["frames"] == 0:
                logger.error("Zero-length audio: %s", stem["filename"])
                all_valid = False
                continue
        return all_valid

    # ------------------------------------------------------------------
    # ID Allocation
    # ------------------------------------------------------------------

    def allocate_object_ids(self, stems: List[Dict]) -> List[Dict]:
        """
        Allocate object group IDs starting from 11.

        Args:
            stems: List of stem info dicts (must be sorted)

        Returns:
            Updated stems list with allocated group IDs

        Per spec (agents.md 7.1, 7.2):
        - Object groups start at 11
        - Stereo stems consume TWO groups (L then R)
        - Node X.1 maps to file X.1.wav
        - LFE special case: 4.1 -> LFE.wav
        """
        next_group_id = 11
        for stem in stems:
            channels = stem.get("channels", 1)
            if channels == 1:
                stem["group_ids"] = [next_group_id]
                stem["wav_names"] = [f"{next_group_id}.1.wav"]
                stem["node_ids"] = [f"{next_group_id}.1"]
                logger.info(
                    "Allocated ID %d.1 -> %s (mono)",
                    next_group_id,
                    stem["filename"],
                )
                next_group_id += 1
            elif channels == 2:
                stem["group_ids"] = [next_group_id, next_group_id + 1]
                stem["wav_names"] = [
                    f"{next_group_id}.1.wav",
                    f"{next_group_id + 1}.1.wav",
                ]
                stem["node_ids"] = [
                    f"{next_group_id}.1",
                    f"{next_group_id + 1}.1",
                ]
                logger.info(
                    "Allocated IDs %d.1 (L), %d.1 (R) -> %s (stereo)",
                    next_group_id,
                    next_group_id + 1,
                    stem["filename"],
                )
                next_group_id += 2
            else:
                raise ValueError(
                    f"Unsupported channel count {channels} for stem "
                    f"{stem['filename']}"
                )
        return stems

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def create_manifest(self, stems: List[Dict]) -> Dict:
        """
        Create session manifest for reproducibility.

        Args:
            stems: List of stem info dicts with allocated IDs

        Returns:
            Session manifest dict
        """
        max_duration = max(s["duration_seconds"] for s in stems) if stems else 0.0

        manifest = {
            "version": "0.1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sample_rate": 48000,
            "max_duration_seconds": max_duration,
            "stems_dir": str(self.stems_dir.resolve()),
            "stem_count": len(stems),
            "object_count": sum(len(s["group_ids"]) for s in stems),
            "stems": stems,
        }
        self.manifest = manifest
        return manifest

    def save_manifest(self, manifest: Dict, output_path: Optional[str] = None):
        """
        Save session manifest to disk.

        Args:
            manifest: Session manifest dict
            output_path: Optional custom path (defaults to project_dir/manifest.json)
        """
        if output_path is None:
            out = self.project_dir / "manifest.json"
        else:
            out = Path(output_path)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info("Manifest saved to %s", out)

    # ------------------------------------------------------------------
    # Top-level runner
    # ------------------------------------------------------------------

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


# ======================================================================
# Utility functions
# ======================================================================


def compute_audio_hash(filepath: str, chunk_size: int = 65536) -> str:
    """
    Compute SHA-256 hash of an audio file for caching.

    Args:
        filepath: Path to audio file
        chunk_size: Read chunk size in bytes

    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
