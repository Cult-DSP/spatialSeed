"""
SpatialSeed LUSID Scene Writer
===============================
Stage 8: LUSID Scene Assembly

Responsibilities:
- Assemble LUSID scene from keyframes, profiles, and metadata
- Write scene.lusid.json matching LUSID v0.5.x conventions
- Emit delta frames (only changing nodes)
- Include bed/direct-speaker nodes at t=0

Per spec: lowLevelSpecsV1.md § 3, agents.md § 4, 8
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class LUSIDSceneWriter:
    """
    Writes LUSID Scene v0.5.x JSON files.
    
    Per spec (lowLevelSpecsV1.md § 3):
    - version: "0.5"
    - sampleRate: 48000
    - timeUnit: "seconds"
    - frames: delta frames (changing nodes only)
    """
    
    # Direct speaker template (per agents.md § 5)
    DIRECT_SPEAKER_TEMPLATE = [
        {"id": "1.1", "type": "direct_speaker", "speakerLabel": "RC_L", 
         "channelName": "RoomCentricLeft", "channelID": "AC_00011001",
         "cart": [-1.0, 1.0, 0.0]},
        {"id": "2.1", "type": "direct_speaker", "speakerLabel": "RC_R",
         "channelName": "RoomCentricRight", "channelID": "AC_00011002",
         "cart": [1.0, 1.0, 0.0]},
        {"id": "3.1", "type": "direct_speaker", "speakerLabel": "RC_C",
         "channelName": "RoomCentricCenter", "channelID": "AC_00011003",
         "cart": [0.0, 1.0, 0.0]},
        {"id": "5.1", "type": "direct_speaker", "speakerLabel": "RC_Lss",
         "channelName": "RoomCentricLeftSideSurround", "channelID": "AC_00011005",
         "cart": [-1.0, 0.0, 0.0]},
        {"id": "6.1", "type": "direct_speaker", "speakerLabel": "RC_Rss",
         "channelName": "RoomCentricRightSideSurround", "channelID": "AC_00011006",
         "cart": [1.0, 0.0, 0.0]},
        {"id": "7.1", "type": "direct_speaker", "speakerLabel": "RC_Lrs",
         "channelName": "RoomCentricLeftRearSurround", "channelID": "AC_00011007",
         "cart": [-1.0, -1.0, 0.0]},
        {"id": "8.1", "type": "direct_speaker", "speakerLabel": "RC_Rrs",
         "channelName": "RoomCentricRightRearSurround", "channelID": "AC_00011008",
         "cart": [1.0, -1.0, 0.0]},
        {"id": "9.1", "type": "direct_speaker", "speakerLabel": "RC_Lts",
         "channelName": "RoomCentricLeftTopSurround", "channelID": "AC_00011009",
         "cart": [-1.0, 0.0, 1.0]},
        {"id": "10.1", "type": "direct_speaker", "speakerLabel": "RC_Rts",
         "channelName": "RoomCentricRightTopSurround", "channelID": "AC_0001100a",
         "cart": [1.0, 0.0, 1.0]},
    ]
    
    def __init__(self, sample_rate: int = 48000):
        """
        Initialize LUSID scene writer.
        
        Args:
            sample_rate: Audio sample rate (default 48000)
        """
        self.sample_rate = sample_rate
        self.scene = {
            "version": "0.5",
            "sampleRate": sample_rate,
            "timeUnit": "seconds",
            "frames": [],
        }
    
    def create_bed_frame(self) -> Dict:
        """
        Create initial frame with bed/direct-speaker nodes at t=0.
        
        Returns:
            Frame dict with bed nodes
            
        Per spec (agents.md § 2.4, § 5):
        - Always include bed groups 1-10 for ADM compatibility
        - Beds are static (only appear at t=0)
        - LFE is special: node 4.1, type "LFE"
        """
        nodes = []
        
        # Add direct speaker nodes
        nodes.extend(self.DIRECT_SPEAKER_TEMPLATE)
        
        # Add LFE node (special case)
        nodes.append({
            "id": "4.1",
            "type": "LFE",
            # No cart for LFE
        })
        
        return {
            "time": 0.0,
            "nodes": nodes,
        }
    
    def create_audio_object_node(self, node_id: str,
                                 x: float, y: float, z: float,
                                 spread: Optional[float] = None) -> Dict:
        """
        Create audio_object node.
        
        Args:
            node_id: Node ID (e.g., "11.1")
            x, y, z: Cartesian position
            spread: Optional angular spread
            
        Returns:
            Node dict
            
        Per spec (lowLevelSpecsV1.md § 3.3):
        - type: "audio_object"
        - cart: [x, y, z]
        - (future) spread: angular spread
        """
        node = {
            "id": node_id,
            "type": "audio_object",
            "cart": [x, y, z],
        }
        
        # TODO: Add spread parameter when supported
        # if spread is not None:
        #     node["spread"] = spread
        
        return node
    
    def assemble_frames_from_keyframes(self, keyframes_dict: Dict) -> List[Dict]:
        """
        Assemble LUSID frames from keyframe data.
        
        Args:
            keyframes_dict: Dict of {node_id: [Keyframe, ...]}
            
        Returns:
            List of frame dicts sorted by time
            
        Per spec (lowLevelSpecsV1.md § 3.2):
        - Delta frames: frames include changing nodes only
        - Every spatial source must have keyframe at t=0.0
        """
        # Collect all unique timestamps
        all_times = set()
        for keyframes in keyframes_dict.values():
            for kf in keyframes:
                all_times.add(kf.time)
        
        # Sort times
        sorted_times = sorted(all_times)
        
        # Build frames
        frames = []
        
        for t in sorted_times:
            nodes = []
            
            # Add bed frame at t=0
            if t == 0.0:
                bed_frame = self.create_bed_frame()
                nodes.extend(bed_frame["nodes"])
            
            # Add audio objects with keyframes at this time
            for node_id, keyframes in keyframes_dict.items():
                for kf in keyframes:
                    if kf.time == t:
                        node = self.create_audio_object_node(
                            node_id, kf.x, kf.y, kf.z, kf.spread
                        )
                        nodes.append(node)
            
            if nodes:
                frames.append({
                    "time": t,
                    "nodes": nodes,
                })
        
        return frames
    
    def write_scene(self, keyframes_dict: Dict, output_path: str):
        """
        Write complete LUSID scene to JSON file.
        
        Args:
            keyframes_dict: Dict of {node_id: [Keyframe, ...]}
            output_path: Path to write scene.lusid.json
            
        Per spec (agents.md § 4.1):
        - Exact filename: scene.lusid.json
        """
        print("Stage 8: LUSID Scene Assembly")
        
        # Assemble frames
        frames = self.assemble_frames_from_keyframes(keyframes_dict)
        self.scene["frames"] = frames
        
        print(f"  Assembled {len(frames)} frames")
        
        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.scene, f, indent=2)
        
        print(f"  LUSID scene written to {output_path}")
    
    def add_agent_state_trace(self, frame_idx: int, node_id: str, 
                             trace_data: Dict, feature_flag: bool = False):
        """
        Add agent_state trace node (optional, behind feature flag).
        
        Args:
            frame_idx: Frame index to add trace to
            node_id: Node ID for trace (e.g., "11.2")
            trace_data: Trace data dict
            feature_flag: Must be True to enable
            
        Per spec (agents.md § 9.2):
        - agent_state nodes for minimal trace only
        - Keep behind feature flag (can break strict consumers)
        """
        if not feature_flag:
            return
        
        # TODO: Add agent_state node to frame
        # Format: {"id": node_id, "type": "agent_state", ...trace_data}
        pass
    
    def validate_scene(self) -> bool:
        """
        Validate LUSID scene structure.
        
        Returns:
            True if valid, False otherwise
            
        Basic validation:
        - Check required fields
        - Verify all audio objects have t=0 keyframe
        - Check for duplicate node IDs within frames
        - Verify frames are sorted by time
        """
        # TODO: Implement validation
        # - Check version, sampleRate, timeUnit, frames exist
        # - Check frames are sorted by time
        # - Verify all audio objects appear at t=0
        # - Check for duplicate node IDs within frames
        
        return True


def load_direct_speaker_template(template_path: str) -> List[Dict]:
    """
    Load direct speaker template from JSON file.
    
    Args:
        template_path: Path to directSpeakerData.json
        
    Returns:
        List of direct speaker node dicts
        
    Per spec (agents.md § 5):
    - Direct speaker mapping is pluggable
    - Must expand to other mappings beyond current template
    """
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    return template
