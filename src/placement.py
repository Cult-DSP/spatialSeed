"""
SpatialSeed Static Placement
=============================
Stage 6: Static Placement

Responsibilities:
- Produce base cart [x,y,z] for each object
- Respect constraints (no-height, symmetry, etc.)
- Clamp to normalized cube [-1,1]^3
- Log clamp events

Per spec: lowLevelSpecsV1.md 7, agents.md 2.2, 8
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

from src.spf import StyleProfile, clamp_to_cube

logger = logging.getLogger("spatialSeed.placement")


class PlacementEngine:
    """
    Generates static spatial placements from StyleProfiles.

    Per spec (agents.md 2.2):
    - Normalized Cartesian cube: x,y,z in [-1,1]
    - Axes: +X = right, +Y = front, +Z = up
    - Clamp positions to cube; log clamp events
    """

    def __init__(self):
        self.clamp_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Constraint helpers
    # ------------------------------------------------------------------

    @staticmethod
    def apply_front_back_bias(y: float, front_back_bias: float) -> float:
        """
        Modulate Y by front-back bias.

        front_back_bias near 0 -> push objects forward (positive Y).
        front_back_bias near 1 -> allow objects behind listener (negative Y).
        """
        # Scale: bias=0 compresses Y to [0.3, 1.0]; bias=1 keeps original
        min_y = 0.3 * (1.0 - front_back_bias)
        return y * (1.0 - min_y) + min_y if y >= 0 else y * front_back_bias

    @staticmethod
    def apply_height_constraint(z: float, height_usage: float,
                                no_height: bool = False) -> float:
        """Scale Z by height_usage.  If no_height is True, force z=0."""
        if no_height:
            return 0.0
        return z * height_usage

    # ------------------------------------------------------------------
    # Single placement
    # ------------------------------------------------------------------

    def compute_placement(
        self,
        profile: StyleProfile,
        style_vector: np.ndarray,
        no_height: bool = False,
    ) -> Tuple[float, float, float]:
        """
        Compute static placement for a single object.

        Pipeline:
        1. Start with profile's resolved base XYZ.
        2. Apply front-back bias and height scaling from style vector.
        3. Clamp to cube.
        """
        height_usage    = float(style_vector[1])
        front_back_bias = float(style_vector[5])

        x = profile.base_x
        y = self.apply_front_back_bias(profile.base_y, front_back_bias)
        z = self.apply_height_constraint(profile.base_z, height_usage, no_height)

        # Clamp
        xc, yc, zc = clamp_to_cube(x, y, z)
        if (xc, yc, zc) != (x, y, z):
            self.clamp_log.append({
                "node_id": profile.node_id,
                "original": (round(x, 4), round(y, 4), round(z, 4)),
                "clamped": (round(xc, 4), round(yc, 4), round(zc, 4)),
            })

        return (round(xc, 4), round(yc, 4), round(zc, 4))

    # ------------------------------------------------------------------
    # Batch placement
    # ------------------------------------------------------------------

    def compute_all_placements(
        self,
        profiles: Dict[str, StyleProfile],
        style_vector: np.ndarray,
        no_height: bool = False,
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Compute static placements for all objects.

        Returns:
            Dict of {node_id: (x, y, z)}
        """
        print("Stage 6: Static Placement")

        placements: Dict[str, Tuple[float, float, float]] = {}

        for node_id in sorted(profiles.keys()):
            profile = profiles[node_id]
            pos = self.compute_placement(profile, style_vector, no_height)
            placements[node_id] = pos
            print(f"  {node_id}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

        # Report clamp events
        if self.clamp_log:
            logger.warning("Clamped %d positions to cube", len(self.clamp_log))
            for evt in self.clamp_log:
                logger.debug("  %s  %s -> %s", evt["node_id"],
                             evt["original"], evt["clamped"])

        return placements


# ------------------------------------------------------------------
# Utility: stereo-pair symmetric positions
# ------------------------------------------------------------------

def compute_stereo_pair_positions(
    left_profile: StyleProfile,
    right_profile: StyleProfile,
    style_vector: np.ndarray,
    spread: float = 0.3,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Compute symmetric positions for a stereo pair.

    The SPF resolver already applies L/R azimuth offsets, so this is
    mainly a convenience for post-hoc adjustment if needed.
    """
    lx, ly, lz = left_profile.base_x, left_profile.base_y, left_profile.base_z
    rx, ry, rz = right_profile.base_x, right_profile.base_y, right_profile.base_z

    # Enforce symmetry on shared Y and Z
    avg_y = (ly + ry) / 2.0
    avg_z = (lz + rz) / 2.0

    return (
        clamp_to_cube(lx, avg_y, avg_z),
        clamp_to_cube(rx, avg_y, avg_z),
    )
