"""
SpatialSeed LUSID Scene Writer
===============================
Stage 8: LUSID Scene Assembly

Responsibilities:
- Assemble LUSID scene from keyframes, profiles, and metadata
- Write scene.lusid.json matching LUSID v0.5.x conventions
- Emit delta frames (only changing nodes)
- Include bed/direct-speaker nodes at t=0

Per spec: lowLevelSpecsV1.md 3, agents.md 4, 8
Uses LUSID/src/scene.py dataclasses when available, falls back to dicts.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class LUSIDSceneWriter:
    """
    Writes LUSID Scene v0.5.x JSON files.

    Per spec (lowLevelSpecsV1.md 3):
    - version: "0.5"
    - sampleRate: 48000
    - timeUnit: "seconds"
    - frames: delta frames (changing nodes only)
    """

    # Direct speaker template (per agents.md 5, LUSID schema v0.5)
    # NOTE: channelName is NOT in the LUSID schema -- only id/type/cart/speakerLabel/channelID
    DIRECT_SPEAKER_TEMPLATE = [
        {"id": "1.1", "type": "direct_speaker", "speakerLabel": "RC_L",
         "channelID": "AC_00011001", "cart": [-1.0, 1.0, 0.0]},
        {"id": "2.1", "type": "direct_speaker", "speakerLabel": "RC_R",
         "channelID": "AC_00011002", "cart": [1.0, 1.0, 0.0]},
        {"id": "3.1", "type": "direct_speaker", "speakerLabel": "RC_C",
         "channelID": "AC_00011003", "cart": [0.0, 1.0, 0.0]},
        {"id": "5.1", "type": "direct_speaker", "speakerLabel": "RC_Lss",
         "channelID": "AC_00011005", "cart": [-1.0, 0.0, 0.0]},
        {"id": "6.1", "type": "direct_speaker", "speakerLabel": "RC_Rss",
         "channelID": "AC_00011006", "cart": [1.0, 0.0, 0.0]},
        {"id": "7.1", "type": "direct_speaker", "speakerLabel": "RC_Lrs",
         "channelID": "AC_00011007", "cart": [-1.0, -1.0, 0.0]},
        {"id": "8.1", "type": "direct_speaker", "speakerLabel": "RC_Rrs",
         "channelID": "AC_00011008", "cart": [1.0, -1.0, 0.0]},
        {"id": "9.1", "type": "direct_speaker", "speakerLabel": "RC_Lts",
         "channelID": "AC_00011009", "cart": [-1.0, 0.0, 1.0]},
        {"id": "10.1", "type": "direct_speaker", "speakerLabel": "RC_Rts",
         "channelID": "AC_0001100a", "cart": [1.0, 0.0, 1.0]},
    ]

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate

    # ------------------------------------------------------------------
    # Node builders
    # ------------------------------------------------------------------

    @staticmethod
    def _audio_object_node(node_id: str, x: float, y: float, z: float,
                           gain: Optional[float] = None) -> Dict:
        """Build an audio_object node dict."""
        node: Dict = {
            "id": node_id,
            "type": "audio_object",
            "cart": [round(x, 6), round(y, 6), round(z, 6)],
        }
        if gain is not None and gain != 1.0:
            node["gain"] = round(gain, 6)
        return node

    @staticmethod
    def _lfe_node() -> Dict:
        """Build the LFE node (group 4, no position)."""
        return {"id": "4.1", "type": "LFE"}

    # ------------------------------------------------------------------
    # Frame assembly
    # ------------------------------------------------------------------

    def _build_bed_nodes(self) -> List[Dict]:
        """Return list of bed/direct-speaker + LFE nodes for t=0."""
        nodes: List[Dict] = []
        nodes.extend(self.DIRECT_SPEAKER_TEMPLATE)
        nodes.append(self._lfe_node())
        return nodes

    def assemble_frames(self, keyframes_dict: Dict) -> List[Dict]:
        """
        Convert per-node keyframes into LUSID delta frames.

        Args:
            keyframes_dict: {node_id: [Keyframe, ...]} from GestureEngine.

        Returns:
            List of frame dicts sorted by time.

        Logic:
        - Collect every unique timestamp across all nodes.
        - At t=0 inject bed/direct-speaker nodes first.
        - At each timestamp emit only the nodes that have a keyframe there
          (delta-frame contract).
        """
        # Build time -> [node_dict, ...] mapping
        time_to_nodes: Dict[float, List[Dict]] = {}

        for node_id, keyframes in keyframes_dict.items():
            for kf in keyframes:
                t = round(kf.time, 6)
                node = self._audio_object_node(node_id, kf.x, kf.y, kf.z)
                time_to_nodes.setdefault(t, []).append(node)

        # Ensure t=0 exists (should always, but defensive)
        if 0.0 not in time_to_nodes:
            time_to_nodes[0.0] = []

        # Sort by time and build frames
        frames: List[Dict] = []
        for t in sorted(time_to_nodes.keys()):
            nodes = []
            if t == 0.0:
                nodes.extend(self._build_bed_nodes())
            nodes.extend(sorted(time_to_nodes[t], key=lambda n: n["id"]))
            frames.append({"time": t, "nodes": nodes})

        return frames

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_scene(self, keyframes_dict: Dict, output_path: str,
                    metadata: Optional[Dict] = None) -> Dict:
        """
        Write complete LUSID scene to JSON file.

        Args:
            keyframes_dict: {node_id: [Keyframe, ...]}
            output_path:    path for scene.lusid.json
            metadata:       optional top-level metadata dict

        Returns:
            The assembled scene dict (for inspection / tests).
        """
        print("Stage 8: LUSID Scene Assembly")

        frames = self.assemble_frames(keyframes_dict)

        scene: Dict = {
            "version": "0.5",
            "sampleRate": self.sample_rate,
            "timeUnit": "seconds",
            "frames": frames,
        }
        if metadata:
            scene["metadata"] = metadata

        # Count stats
        n_audio_obj = sum(
            1 for f in frames for n in f["nodes"] if n["type"] == "audio_object"
        )
        n_beds = sum(
            1 for f in frames for n in f["nodes"]
            if n["type"] in ("direct_speaker", "LFE")
        )
        print(f"  {len(frames)} frames, {n_audio_obj} audio-object entries, "
              f"{n_beds} bed/LFE entries")

        # Write
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as fh:
            json.dump(scene, fh, indent=2)
        print(f"  Written to {out}")

        return scene

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_scene(scene: Dict) -> List[str]:
        """
        Validate a LUSID scene dict.

        Returns a list of error strings (empty = valid).
        Checks:
        - Required top-level keys
        - Frames sorted by time
        - Every audio_object group has a keyframe at t=0
        - No duplicate node IDs within a single frame
        - Bed/LFE presence at t=0
        """
        errors: List[str] = []

        # Top-level keys
        for key in ("version", "frames"):
            if key not in scene:
                errors.append(f"Missing top-level key '{key}'")
        if scene.get("version") != "0.5":
            errors.append(f"Expected version '0.5', got '{scene.get('version')}'")

        frames = scene.get("frames", [])
        if not frames:
            errors.append("Scene has no frames")
            return errors

        # Frames sorted
        times = [f["time"] for f in frames]
        if times != sorted(times):
            errors.append("Frames are not sorted by time")

        # t=0 checks
        t0_frame = frames[0] if frames[0]["time"] == 0.0 else None
        if t0_frame is None:
            errors.append("First frame is not at t=0.0")
        else:
            t0_ids = {n["id"] for n in t0_frame["nodes"]}
            # Check beds present
            for bed_id in ["1.1", "2.1", "3.1", "5.1", "6.1", "7.1", "8.1",
                           "9.1", "10.1"]:
                if bed_id not in t0_ids:
                    errors.append(f"Bed node {bed_id} missing at t=0")
            if "4.1" not in t0_ids:
                errors.append("LFE node 4.1 missing at t=0")

            # Every audio_object group that appears anywhere must also appear at t=0
            all_ao_ids: set = set()
            for f in frames:
                for n in f["nodes"]:
                    if n["type"] == "audio_object":
                        all_ao_ids.add(n["id"])
            missing_at_t0 = all_ao_ids - t0_ids
            for mid in sorted(missing_at_t0):
                errors.append(f"audio_object {mid} missing at t=0")

        # Duplicate IDs within frames
        for f in frames:
            ids_in_frame = [n["id"] for n in f["nodes"]]
            seen: set = set()
            for nid in ids_in_frame:
                if nid in seen:
                    errors.append(f"Duplicate node ID '{nid}' in frame t={f['time']}")
                seen.add(nid)

        return errors
