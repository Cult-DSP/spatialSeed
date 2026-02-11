"""
SpatialSeed Static Placement
=============================
Stage 6: Static Placement

Responsibilities:
- Produce base cart [x,y,z] for each object
- Respect constraints (no-height, symmetry, etc.)
- Clamp to normalized cube [-1,1]³
- Log clamp events

Per spec: lowLevelSpecsV1.md § 7, agents.md § 2.2, § 8
"""

import numpy as np
from typing import Dict, List, Tuple
import logging


class PlacementEngine:
    """
    Generates static spatial placements from StyleProfiles.
    
    Per spec (agents.md § 2.2):
    - Normalized Cartesian cube: x,y,z ∈ [-1,1]
    - Axes: +X = right, +Y = front, +Z = up
    - Clamp positions to cube; log clamp events
    """
    
    def __init__(self):
        """Initialize placement engine."""
        self.clamp_log = []
    
    def clamp_to_cube(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Clamp position to normalized cube [-1,1]³.
        
        Args:
            x, y, z: Input coordinates
            
        Returns:
            Clamped (x, y, z)
            
        Per spec (agents.md § 2.2, § 11):
        - Clamp positions to the cube
        - Log clamp events for diagnostics
        """
        x_clamped = np.clip(x, -1.0, 1.0)
        y_clamped = np.clip(y, -1.0, 1.0)
        z_clamped = np.clip(z, -1.0, 1.0)
        
        # Log if clamping occurred
        if x != x_clamped or y != y_clamped or z != z_clamped:
            self.clamp_log.append({
                "original": (x, y, z),
                "clamped": (x_clamped, y_clamped, z_clamped),
            })
        
        return (x_clamped, y_clamped, z_clamped)
    
    def apply_symmetry_constraint(self, positions: List[Tuple], 
                                  symmetry_bias: float) -> List[Tuple]:
        """
        Apply symmetry constraints to positions.
        
        Args:
            positions: List of (x, y, z) tuples
            symmetry_bias: Symmetry bias from style vector [0,1]
                          0 = fully asymmetric, 1 = enforce symmetry
        
        Returns:
            Adjusted positions
            
        Per spec (seed_matrix.py):
        - z[4]: symmetry bias (symmetric → asymmetric)
        """
        # TODO: Implement symmetry logic
        # - If symmetry_bias is high:
        #   - Mirror positions across x=0 plane
        #   - Pair objects symmetrically
        # - If low: allow asymmetric placement
        
        return positions
    
    def apply_front_back_bias(self, y: float, front_back_bias: float) -> float:
        """
        Apply front-back bias to Y coordinate.
        
        Args:
            y: Original Y coordinate
            front_back_bias: Front-back bias from style vector [0,1]
                           0 = front-heavy, 1 = surround
        
        Returns:
            Adjusted Y coordinate
        """
        # TODO: Implement front-back bias
        # - If front_back_bias is low: push objects forward (y > 0)
        # - If high: distribute around listener (y can be negative)
        
        # Placeholder: linear push/pull
        adjusted_y = y * (0.5 + 0.5 * front_back_bias)
        
        return adjusted_y
    
    def apply_height_constraint(self, z: float, height_usage: float,
                               no_height: bool = False) -> float:
        """
        Apply height constraints.
        
        Args:
            z: Original Z coordinate
            height_usage: Height usage from style vector [0,1]
            no_height: If True, force z=0 (floor level)
        
        Returns:
            Adjusted Z coordinate
        """
        if no_height:
            return 0.0
        
        # Scale height by usage factor
        adjusted_z = z * height_usage
        
        return adjusted_z
    
    def compute_placement(self, profile, style_vector: np.ndarray,
                         mix_features: Dict = None) -> Tuple[float, float, float]:
        """
        Compute static placement for a single object.
        
        Args:
            profile: StyleProfile instance
            style_vector: Style vector z
            mix_features: Optional stereo mix features for context
            
        Returns:
            Tuple of (x, y, z) in normalized cube
            
        Pipeline:
        1. Start with profile's base XYZ
        2. Apply style vector modulations
        3. Apply constraints (symmetry, front-back, height)
        4. Clamp to cube
        """
        # Extract style vector components
        placement_spread = style_vector[0]
        height_usage = style_vector[1]
        symmetry_bias = style_vector[4]
        front_back_bias = style_vector[5]
        ensemble_cohesion = style_vector[6]
        
        # Start with profile base
        x = profile.base_x
        y = profile.base_y
        z = profile.base_z
        
        # TODO: Apply style modulations
        # - Add controlled randomness based on placement_spread
        # - Adjust based on ensemble_cohesion (grouped vs dispersed)
        # - Consider mix features (stereo width, L/R balance)
        
        # Apply constraints
        y = self.apply_front_back_bias(y, front_back_bias)
        z = self.apply_height_constraint(z, height_usage)
        
        # Clamp to cube
        x, y, z = self.clamp_to_cube(x, y, z)
        
        return (x, y, z)
    
    def compute_all_placements(self, profiles: Dict, style_vector: np.ndarray,
                              mir_summary: Dict = None) -> Dict[str, Tuple]:
        """
        Compute static placements for all objects.
        
        Args:
            profiles: Dict of StyleProfiles keyed by node_id
            style_vector: Style vector z
            mir_summary: Optional MIR summary with mix features
            
        Returns:
            Dict of {node_id: (x, y, z)} placements
        """
        print("Stage 6: Static Placement")
        
        # Get mix features if available
        mix_features = mir_summary.get("mix", {}) if mir_summary else {}
        
        placements = {}
        
        for node_id, profile in profiles.items():
            x, y, z = self.compute_placement(profile, style_vector, mix_features)
            placements[node_id] = (x, y, z)
            print(f"  {node_id}: ({x:.3f}, {y:.3f}, {z:.3f})")
        
        # Log clamp events
        if self.clamp_log:
            logging.warning(f"Clamped {len(self.clamp_log)} positions to cube")
            for event in self.clamp_log:
                logging.debug(f"  {event['original']} → {event['clamped']}")
        
        return placements


def normalize_vector(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Normalize a direction vector to unit length.
    
    Args:
        x, y, z: Vector components
        
    Returns:
        Normalized (x, y, z)
        
    Per spec (lowLevelSpecsV1.md):
    - Vectors are normalized to unit length by the renderer
    - But we can pre-normalize for clarity
    """
    magnitude = np.sqrt(x**2 + y**2 + z**2)
    
    if magnitude == 0:
        return (0.0, 1.0, 0.0)  # Default to front
    
    return (x / magnitude, y / magnitude, z / magnitude)


def compute_stereo_pair_positions(left_profile, right_profile,
                                  style_vector: np.ndarray,
                                  spread: float = 0.3) -> Tuple[Tuple, Tuple]:
    """
    Compute symmetric positions for stereo pair.
    
    Args:
        left_profile: StyleProfile for left channel
        right_profile: StyleProfile for right channel
        style_vector: Style vector z
        spread: Stereo spread (angular separation)
        
    Returns:
        Tuple of ((x_left, y_left, z_left), (x_right, y_right, z_right))
        
    Per spec (agents.md § 2.3):
    - Stereo stems become two objects
    - Can apply stereo-aware placement logic
    """
    # TODO: Compute symmetric positions
    # - Use base position from one profile
    # - Mirror across x=0 with spread
    # - Maintain same y and z
    
    base_x = left_profile.base_x
    base_y = left_profile.base_y
    base_z = left_profile.base_z
    
    x_left = base_x - spread
    x_right = base_x + spread
    
    return ((x_left, base_y, base_z), (x_right, base_y, base_z))
