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
    
    def __init__(self, z_dim: int = 8, default_u: float = 0.5, default_v: float = 0.3):
        """
        Initialize Seed Matrix mapper.
        
        Args:
            z_dim: Dimension of style vector
            default_u: Default u parameter
            default_v: Default v parameter
        """
        self.Z_DIM = z_dim
        self.default_u = default_u
        self.default_v = default_v
    
    def map_uv_to_z(self, u: float, v: float) -> np.ndarray:
        """
        Map (u,v) selection to style vector z (UPGRADED v2).
        
        Args:
            u: Aesthetic variation [0,1]
            v: Dynamic immersion [0,1]
            
        Returns:
            Style vector z, shape (Z_DIM,)
            
        Per spec (agents.md § 14.2, upgraded v2):
        Smooth nonlinear mapping with perceptual scaling and interaction terms.
        
        Style vector components (v2 upgraded):
        - z[0]: placement spread (more with u, capped by v for conservative static scenes)
        - z[1]: height usage (more with v, scaled by u for experimental)
        - z[2]: motion intensity (primarily v, boosted by u for experimental dynamics)
        - z[3]: motion complexity (only with high u AND v; avoid needless complexity)
        - z[4]: symmetry breaking (more asymmetry with experimental u)
        - z[5]: front-back bias (forward with conservative u; variance with experimental)
        - z[6]: ensemble cohesion (NOW ACTIVE; tight with v, loose with u)
        - z[7]: mir coupling (stronger with dynamic + experimental)
        
        Design rationale (agents.md § 14.2):
        u = 0 (Conservative): tight cluster, very symmetric, front-heavy, low complexity
        u = 1 (Experimental): wide distribution, asymmetric, varied positions, high complexity
        v = 0 (Static): no motion, ground level, no reactivity
        v = 1 (Immersive): multiple orbits, full 3D, strong MIR reactivity
        """
        # Clamp inputs
        u = np.clip(u, 0.0, 1.0)
        v = np.clip(v, 0.0, 1.0)
        
        # --- Smooth activation curves (perceptually natural control) ---
        
        def smoothstep(x):
            """Hermite smoothstep: 3x² - 2x³ (smooth S-curve)"""
            return 3 * x**2 - 2 * x**3
        
        def sigmoid_like(x):
            """Sigmoid-like curve using tanh: maps [0,1] to [0,1]"""
            return np.tanh(2 * x - 1) * 0.5 + 0.5
        
        u_smooth = sigmoid_like(u)  # Perceptually smoother u scaling
        v_smooth = smoothstep(v)     # Smooth v transitions
        
        # --- Build style vector with interaction terms ---
        z = np.zeros(self.Z_DIM, dtype=np.float32)
        
        # z[0]: placement_spread
        # More spread with u, but conservative static scenes stay tight
        z[0] = u_smooth * (0.8 + 0.2 * v_smooth)
        
        # z[1]: height_usage
        # More height with v (dynamic immersion), scaled by u (experimental)
        z[1] = v_smooth * (0.5 + 0.5 * u_smooth)
        
        # z[2]: motion_intensity
        # Primarily driven by v, boosted by u for experimental dynamics
        z[2] = v_smooth * (0.6 + 0.4 * u_smooth)
        
        # z[3]: motion_complexity
        # Only emerge when BOTH u and v are high (avoid complexity creep at medium values)
        z[3] = (u_smooth * v_smooth) ** 1.5
        
        # z[4]: symmetry_breaking (1 - u_smooth = more symmetry when conservative)
        z[4] = (1 - u_smooth) * 0.8
        
        # z[5]: front_back_bias
        # More forward bias with conservative u; experimentation adds spatial variance
        z[5] = 0.5 + 0.2 * (1 - u_smooth) + 0.15 * u_smooth * np.sin(3 * u)
        
        # z[6]: ensemble_cohesion (NOW VARIES!)
        # Tight cohesion when v=0 (static), loose when v=1 (dispersed)
        # Conservative u keeps them tighter
        z[6] = (1 - v_smooth) * (0.8 + 0.2 * (1 - u_smooth))
        
        # z[7]: mir_coupling
        # Stronger coupling with both dynamics (v) and experimentation (u)
        z[7] = (u_smooth * v_smooth) ** 0.8
        
        # Ensure all values are in [0, 1]
        z = np.clip(z, 0.0, 1.0)
        
        return z
    
    def get_default_uv(self) -> Tuple[float, float]:
        """
        Get default (u,v) selection.
        
        Returns:
            Default (u, v) tuple
        """
        return (self.default_u, self.default_v)
    
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
