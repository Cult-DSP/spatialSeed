"""
SpatialSeed Seed Matrix
========================
Stage 4: Seed Matrix Selection

Responsibilities:
- Map user-selected (u,v) point to style vector z
- u axis: aesthetic variation (conservative → experimental)
- v axis: dynamic immersion (static → enveloping/animated)

Per spec: DesignSpecV1.md § 2.2, agents.md § 8
"""

import numpy as np
from typing import Tuple


class SeedMatrix:
    """
    Maps 2D Seed Matrix selection to low-dimensional style vector.
    
    Per spec (DesignSpecV1.md § 2.2):
    - u ∈ [0,1]: aesthetic variation (0=conservative, 1=experimental)
    - v ∈ [0,1]: dynamic immersion (0=static, 1=enveloping/animated)
    - Output: style vector z for use across all instruments
    """
    
    # Style vector dimension (v1: small, expandable)
    Z_DIM = 8
    
    def __init__(self):
        """Initialize Seed Matrix mapper."""
        pass
    
    def map_uv_to_z(self, u: float, v: float) -> np.ndarray:
        """
        Map (u,v) selection to style vector z.
        
        Args:
            u: Aesthetic variation [0,1]
            v: Dynamic immersion [0,1]
            
        Returns:
            Style vector z, shape (Z_DIM,)
            
        Per spec (DesignSpecV1.md § 7):
        - v1: analytic mapping f(u,v)
        - Future: replace with learned latent space while preserving UX
        
        Style vector components (v1 example):
        - z[0]: placement spread (conservative → wide)
        - z[1]: height usage (floor-level → full 3D)
        - z[2]: motion intensity (controlled by v primarily)
        - z[3]: motion complexity (paths vs orbits vs chaotic)
        - z[4]: symmetry bias (symmetric → asymmetric)
        - z[5]: front-back bias (front-heavy → surround)
        - z[6]: ensemble cohesion (grouped → dispersed)
        - z[7]: modulation sensitivity (MIR → motion coupling)
        """
        # Clamp inputs
        u = np.clip(u, 0.0, 1.0)
        v = np.clip(v, 0.0, 1.0)
        
        # TODO: Implement analytic mapping
        # Example approach:
        # - z[0] = 0.3 + 0.7 * u  (placement spread)
        # - z[1] = 0.2 + 0.8 * u  (height usage)
        # - z[2] = v  (motion intensity, primarily v-driven)
        # - z[3] = u * v  (motion complexity, interaction term)
        # - z[4] = 1.0 - u * 0.5  (symmetry bias)
        # - z[5] = 0.5 + u * 0.3  (front-back bias)
        # - z[6] = u  (ensemble cohesion)
        # - z[7] = v * 0.8  (modulation sensitivity)
        
        z = np.zeros(self.Z_DIM, dtype=np.float32)
        z[0] = 0.3 + 0.7 * u  # placement spread
        z[1] = 0.2 + 0.8 * u  # height usage
        z[2] = v              # motion intensity
        z[3] = u * v          # motion complexity
        z[4] = 1.0 - u * 0.5  # symmetry bias
        z[5] = 0.5 + u * 0.3  # front-back bias
        z[6] = u              # ensemble cohesion
        z[7] = v * 0.8        # modulation sensitivity
        
        return z
    
    def get_default_uv(self) -> Tuple[float, float]:
        """
        Get default (u,v) selection.
        
        Returns:
            Default (u, v) tuple
            
        Default: moderate aesthetic, low-moderate animation
        """
        return (0.5, 0.3)
    
    def describe_z(self, z: np.ndarray) -> dict:
        """
        Generate human-readable description of style vector.
        
        Args:
            z: Style vector
            
        Returns:
            Dict with component descriptions
        """
        descriptions = {
            "placement_spread": f"{z[0]:.2f} (conservative → wide)",
            "height_usage": f"{z[1]:.2f} (floor → full 3D)",
            "motion_intensity": f"{z[2]:.2f} (static → animated)",
            "motion_complexity": f"{z[3]:.2f} (simple → complex)",
            "symmetry_bias": f"{z[4]:.2f} (asymmetric → symmetric)",
            "front_back_bias": f"{z[5]:.2f} (front → surround)",
            "ensemble_cohesion": f"{z[6]:.2f} (grouped → dispersed)",
            "modulation_sensitivity": f"{z[7]:.2f} (low → high MIR coupling)",
        }
        
        return descriptions
    
    def save_selection(self, u: float, v: float, z: np.ndarray, output_path: str):
        """
        Save Seed Matrix selection for reproducibility.
        
        Args:
            u: Selected u value
            v: Selected v value
            z: Computed style vector
            output_path: Path to write selection JSON
            
        Per spec (agents.md § 8):
        - Store minimal trace for reproducibility
        """
        import json
        
        selection = {
            "seed_matrix": {
                "u": float(u),
                "v": float(v),
            },
            "style_vector": {
                "z": z.tolist(),
                "dim": self.Z_DIM,
                "descriptions": self.describe_z(z),
            },
        }
        
        with open(output_path, 'w') as f:
            json.dump(selection, f, indent=2)


def interpolate_between_selections(uv1: Tuple[float, float], 
                                   uv2: Tuple[float, float], 
                                   alpha: float) -> Tuple[float, float]:
    """
    Interpolate between two Seed Matrix selections.
    
    Args:
        uv1: First (u,v) selection
        uv2: Second (u,v) selection
        alpha: Interpolation factor [0,1]
        
    Returns:
        Interpolated (u,v) point
        
    Useful for exploring the space or creating variations.
    """
    u = (1 - alpha) * uv1[0] + alpha * uv2[0]
    v = (1 - alpha) * uv1[1] + alpha * uv2[1]
    
    return (u, v)
