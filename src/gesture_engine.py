"""
SpatialSeed Gesture Engine
===========================
Stage 7: Gesture Generation (Sparse Keyframes)

Responsibilities:
- Generate sparse keyframes for object motion
- Emit delta frames (only nodes that changed)
- Ensure t=0.0 keyframe for each source
- Motion intensity governed by Seed Matrix v axis

Per spec: lowLevelSpecsV1.md § 0, 3.2, agents.md § 8
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Keyframe:
    """
    Spatial keyframe for an object.
    """
    time: float  # Time in seconds
    x: float
    y: float
    z: float
    spread: Optional[float] = None  # Optional spread parameter


class GestureEngine:
    """
    Generates sparse spatial keyframes for object motion.
    
    Per spec (lowLevelSpecsV1.md § 0):
    - Motion is sparse keyframes only (no dense sampling)
    - Emit delta frames: only nodes that changed
    - Ensure t=0.0 keyframe for each source
    """
    
    # Keyframe emission thresholds (per agents.md § 13)
    POS_EPSILON = 0.01  # Position change threshold (normalized units)
    SPREAD_EPSILON = 0.02  # Spread change threshold
    
    def __init__(self, duration_seconds: float):
        """
        Initialize gesture engine.
        
        Args:
            duration_seconds: Total duration of the scene
        """
        self.duration = duration_seconds
        self.keyframes = {}  # Dict[node_id, List[Keyframe]]
    
    def generate_static_gesture(self, node_id: str, 
                               x: float, y: float, z: float,
                               spread: float) -> List[Keyframe]:
        """
        Generate static gesture (single keyframe at t=0).
        
        Args:
            node_id: Node ID
            x, y, z: Static position
            spread: Static spread
            
        Returns:
            List containing single keyframe at t=0
            
        Per spec (agents.md § 2.3):
        - Every spatial source must have keyframe at t=0.0
        """
        return [Keyframe(time=0.0, x=x, y=y, z=z, spread=spread)]
    
    def generate_drift_gesture(self, node_id: str,
                              start_pos: Tuple[float, float, float],
                              spread: float,
                              profile,
                              mir_features: Dict) -> List[Keyframe]:
        """
        Generate gentle drift motion.
        
        Args:
            node_id: Node ID
            start_pos: Starting position (x, y, z)
            spread: Spread value
            profile: StyleProfile instance
            mir_features: MIR features for modulation
            
        Returns:
            List of keyframes with gentle drift
            
        Drift: slow, smooth motion around base position.
        """
        keyframes = []
        
        # Initial keyframe at t=0
        x0, y0, z0 = start_pos
        keyframes.append(Keyframe(time=0.0, x=x0, y=y0, z=z0, spread=spread))
        
        # TODO: Generate sparse drift keyframes
        # - Sample keyframes at regular intervals (e.g., every 4-8 seconds)
        # - Apply small random offsets around base position
        # - Modulate by MIR features (energy, flux) if profile has coupling
        # - Apply emission thresholds (only emit if change > POS_EPSILON)
        
        # Placeholder: add one drift keyframe at midpoint
        if self.duration > 4.0:
            t_mid = self.duration / 2.0
            x_drift = x0 + np.random.uniform(-0.1, 0.1)
            y_drift = y0 + np.random.uniform(-0.05, 0.05)
            z_drift = z0
            
            keyframes.append(Keyframe(time=t_mid, x=x_drift, y=y_drift, z=z_drift, spread=spread))
        
        return keyframes
    
    def generate_orbit_gesture(self, node_id: str,
                              center_pos: Tuple[float, float, float],
                              spread: float,
                              profile,
                              mir_features: Dict) -> List[Keyframe]:
        """
        Generate orbital motion.
        
        Args:
            node_id: Node ID
            center_pos: Orbit center (x, y, z)
            spread: Spread value
            profile: StyleProfile instance
            mir_features: MIR features for modulation
            
        Returns:
            List of keyframes with orbital motion
            
        Orbit: circular or elliptical path around center.
        """
        keyframes = []
        
        cx, cy, cz = center_pos
        
        # Orbit parameters
        radius = 0.3  # Base radius
        orbit_period = 8.0  # Seconds per orbit
        
        # TODO: Generate orbit keyframes
        # - Sample keyframes along orbital path
        # - Modulate radius and speed by motion_intensity
        # - Consider MIR coupling (e.g., energy affects radius)
        # - Apply emission thresholds
        
        # Placeholder: sample 4 keyframes around orbit
        num_samples = 4
        for i in range(num_samples + 1):
            t = (i / num_samples) * min(self.duration, orbit_period)
            angle = (i / num_samples) * 2 * np.pi
            
            x = cx + radius * np.cos(angle)
            y = cy + radius * np.sin(angle)
            z = cz
            
            keyframes.append(Keyframe(time=t, x=x, y=y, z=z, spread=spread))
        
        return keyframes
    
    def generate_reactive_gesture(self, node_id: str,
                                  base_pos: Tuple[float, float, float],
                                  spread: float,
                                  profile,
                                  mir_features: Dict) -> List[Keyframe]:
        """
        Generate reactive motion (MIR-driven).
        
        Args:
            node_id: Node ID
            base_pos: Base position (x, y, z)
            spread: Base spread value
            profile: StyleProfile instance
            mir_features: MIR features for modulation
            
        Returns:
            List of keyframes with MIR-reactive motion
            
        Reactive: motion and spread coupled to MIR features.
        """
        keyframes = []
        
        x0, y0, z0 = base_pos
        
        # Initial keyframe
        keyframes.append(Keyframe(time=0.0, x=x0, y=y0, z=z0, spread=spread))
        
        # TODO: Generate MIR-reactive keyframes
        # - Analyze MIR features over time (onset events, energy envelope, etc.)
        # - Generate keyframes at significant MIR events
        # - Modulate position and spread based on feature values
        # - Use profile.mir_coupling to scale response
        # - Apply emission thresholds
        
        # Placeholder: static for now (requires time-series MIR data)
        
        return keyframes
    
    def generate_gesture(self, node_id: str,
                        placement: Tuple[float, float, float],
                        profile,
                        mir_features: Dict) -> List[Keyframe]:
        """
        Generate gesture for a single object based on motion type.
        
        Args:
            node_id: Node ID
            placement: Static placement (x, y, z)
            profile: StyleProfile instance
            mir_features: MIR features dict
            
        Returns:
            List of keyframes
            
        Motion types: static, drift, orbit, reactive
        """
        motion_type = profile.motion_type
        motion_intensity = profile.motion_intensity
        spread = profile.spread
        
        # If motion intensity is very low, force static
        if motion_intensity < 0.05:
            return self.generate_static_gesture(node_id, *placement, spread)
        
        # Dispatch to appropriate generator
        if motion_type == "static":
            return self.generate_static_gesture(node_id, *placement, spread)
        
        elif motion_type == "gentle_drift" or motion_type == "drift":
            return self.generate_drift_gesture(node_id, placement, spread, profile, mir_features)
        
        elif motion_type == "orbit":
            return self.generate_orbit_gesture(node_id, placement, spread, profile, mir_features)
        
        elif motion_type == "reactive":
            return self.generate_reactive_gesture(node_id, placement, spread, profile, mir_features)
        
        else:
            # Unknown motion type: fallback to static
            return self.generate_static_gesture(node_id, *placement, spread)
    
    def generate_all_gestures(self, placements: Dict,
                             profiles: Dict,
                             mir_summary: Dict) -> Dict[str, List[Keyframe]]:
        """
        Generate gestures for all objects.
        
        Args:
            placements: Dict of {node_id: (x,y,z)}
            profiles: Dict of StyleProfiles
            mir_summary: MIR summary dict
            
        Returns:
            Dict of {node_id: [Keyframe, ...]}
        """
        print("Stage 7: Gesture Generation (Sparse Keyframes)")
        
        for node_id in placements.keys():
            placement = placements[node_id]
            profile = profiles[node_id]
            mir_features = mir_summary["stems"].get(node_id, {}).get("features", {})
            
            keyframes = self.generate_gesture(node_id, placement, profile, mir_features)
            self.keyframes[node_id] = keyframes
            
            print(f"  {node_id}: {len(keyframes)} keyframes ({profile.motion_type})")
        
        return self.keyframes
    
    def apply_emission_thresholds(self):
        """
        Apply emission thresholds to reduce keyframe count.
        
        Per spec (agents.md § 13):
        - Only emit keyframes if change > POS_EPSILON or SPREAD_EPSILON
        - Keep t=0 keyframe always
        
        Modifies self.keyframes in place.
        """
        # TODO: For each object's keyframe list:
        #   - Keep t=0 keyframe
        #   - For subsequent keyframes, check if delta exceeds thresholds
        #   - Remove keyframes below threshold
        
        pass
    
    def get_keyframe_stats(self) -> Dict:
        """
        Get statistics about generated keyframes.
        
        Returns:
            Dict with keyframe statistics
        """
        total_keyframes = sum(len(kfs) for kfs in self.keyframes.values())
        static_objects = sum(1 for kfs in self.keyframes.values() if len(kfs) == 1)
        
        return {
            "total_objects": len(self.keyframes),
            "total_keyframes": total_keyframes,
            "static_objects": static_objects,
            "animated_objects": len(self.keyframes) - static_objects,
            "avg_keyframes_per_object": total_keyframes / len(self.keyframes) if self.keyframes else 0,
        }


def interpolate_keyframes(kf1: Keyframe, kf2: Keyframe, alpha: float) -> Keyframe:
    """
    Interpolate between two keyframes.
    
    Args:
        kf1: First keyframe
        kf2: Second keyframe
        alpha: Interpolation factor [0,1]
        
    Returns:
        Interpolated keyframe
        
    Useful for preview or debug visualization.
    """
    t = (1 - alpha) * kf1.time + alpha * kf2.time
    x = (1 - alpha) * kf1.x + alpha * kf2.x
    y = (1 - alpha) * kf1.y + alpha * kf2.y
    z = (1 - alpha) * kf1.z + alpha * kf2.z
    
    spread = None
    if kf1.spread is not None and kf2.spread is not None:
        spread = (1 - alpha) * kf1.spread + alpha * kf2.spread
    
    return Keyframe(time=t, x=x, y=y, z=z, spread=spread)
