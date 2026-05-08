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

from src.spatial.spf import StyleProfile, clamp_to_cube

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
        self.category_spread_factor = {
            "vocals": 0.85,
            "bass": 0.7,
            "drums": 0.9,
            "percussion": 0.95,
            "guitar": 1.0,
            "keys": 1.0,
            "strings": 1.05,
            "pads": 1.15,
            "fx": 1.2,
            "ambience": 1.25,
        }
        self.category_distance_factor = {
            "vocals": 0.9,
            "bass": 0.82,
            "drums": 0.9,
            "percussion": 0.95,
            "guitar": 1.0,
            "keys": 1.0,
            "strings": 1.05,
            "pads": 1.12,
            "fx": 1.18,
            "ambience": 1.2,
        }
        self.category_height_bias = {
            "vocals": 0.05,
            "bass": -0.12,
            "drums": -0.06,
            "percussion": -0.04,
            "guitar": 0.02,
            "keys": 0.04,
            "strings": 0.08,
            "pads": 0.12,
            "fx": 0.15,
            "ambience": 0.18,
        }
        self.role_distance_factor = {
            "lead": 0.9,
            "bass": 0.85,
            "rhythm": 1.0,
            "fx": 1.1,
            "ambience": 1.15,
        }

    # ------------------------------------------------------------------
    # Style vector helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_z(style_vector: np.ndarray, index: int, default: float = 0.0) -> float:
        """Safely read a style vector index with fallback."""
        try:
            if style_vector is None or len(style_vector) <= index:
                return default
            return float(style_vector[index])
        except Exception:
            return default

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

    def apply_height_band(self, z: float, category: str, role: str,
                          height_usage: float) -> float:
        """Apply a gentle category-based height bias before scaling."""
        bias = self.category_height_bias.get(category, 0.0)
        if role in ("lead", "fx"):
            bias += 0.03
        bias_scale = 0.4 + 0.6 * height_usage
        return z + bias * bias_scale

    @staticmethod
    def apply_spread_and_cohesion(x: float, y: float,
                                  placement_spread: float,
                                  ensemble_cohesion: float,
                                  symmetry_bias: float) -> Tuple[float, float]:
        """
        Apply spread, cohesion, and symmetry bias to X/Y.

        placement_spread: more spread with higher values (wider field)
        ensemble_cohesion: higher values pull positions toward center
        symmetry_bias: higher values reduce lateral asymmetry (conservative)
        """
        spread_factor = 0.7 + 0.6 * placement_spread      # [0.7, 1.3]
        cohesion_factor = 1.0 - 0.4 * ensemble_cohesion   # [0.6, 1.0]
        symmetry_factor = 1.0 - 0.35 * symmetry_bias      # [0.65, 1.0]

        x_scaled = x * spread_factor * cohesion_factor * symmetry_factor
        y_scaled = y * spread_factor * cohesion_factor

        return x_scaled, y_scaled

    def apply_distance_scaling(self, x: float, y: float, z: float,
                               placement_spread: float,
                               ensemble_cohesion: float,
                               category: str,
                               role: str) -> Tuple[float, float, float]:
        """Scale radial distance to preserve depth cues."""
        base_factor = 0.85 + 0.3 * placement_spread - 0.2 * ensemble_cohesion
        category_factor = self.category_distance_factor.get(category, 1.0)
        role_factor = self.role_distance_factor.get(role, 1.0)
        distance_factor = base_factor * category_factor * role_factor
        return (x * distance_factor, y * distance_factor, z * distance_factor)

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
        placement_spread = self._safe_z(style_vector, 0, 0.5)
        height_usage = self._safe_z(style_vector, 1, 0.5)
        symmetry_bias = self._safe_z(style_vector, 4, 0.5)
        front_back_bias = self._safe_z(style_vector, 5, 0.5)
        ensemble_cohesion = self._safe_z(style_vector, 6, 0.5)

        x, y = self.apply_spread_and_cohesion(
            profile.base_x,
            profile.base_y,
            placement_spread=placement_spread,
            ensemble_cohesion=ensemble_cohesion,
            symmetry_bias=symmetry_bias,
        )
        z = self.apply_height_band(profile.base_z, profile.category, profile.role, height_usage)
        z = self.apply_height_constraint(z, height_usage, no_height)
        x, y, z = self.apply_distance_scaling(
            x,
            y,
            z,
            placement_spread=placement_spread,
            ensemble_cohesion=ensemble_cohesion,
            category=profile.category,
            role=profile.role,
        )
        y = self.apply_front_back_bias(y, front_back_bias)

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

        self.apply_front_zone_density(placements, profiles, style_vector)
        self.apply_inter_object_spacing(placements, profiles)

        # Report clamp events
        if self.clamp_log:
            logger.warning("Clamped %d positions to cube", len(self.clamp_log))
            for evt in self.clamp_log:
                logger.debug("  %s  %s -> %s", evt["node_id"],
                             evt["original"], evt["clamped"])

        return placements

    # ------------------------------------------------------------------
    # Post-processing (batch)
    # ------------------------------------------------------------------

    def apply_front_zone_density(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        profiles: Dict[str, StyleProfile],
        style_vector: np.ndarray,
    ) -> None:
        """Reduce front-zone crowding when many sources exist."""
        if len(placements) < 20:
            return

        placement_spread = self._safe_z(style_vector, 0, 0.5)
        ensemble_cohesion = self._safe_z(style_vector, 6, 0.5)
        push = 0.08 + 0.12 * placement_spread
        push *= (0.7 + 0.3 * (1 - ensemble_cohesion))

        for node_id, (x, y, z) in placements.items():
            profile = profiles[node_id]
            if profile.role in ("lead", "bass") or profile.category in ("vocals", "bass"):
                continue
            if y > 0.2:
                y = max(-1.0, y - push)
                placements[node_id] = clamp_to_cube(x, y, z)

    def apply_inter_object_spacing(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        profiles: Dict[str, StyleProfile],
        min_distance: float = 0.08,
        iterations: int = 2,
    ) -> None:
        """Apply a lightweight repulsion to avoid stacking objects."""
        node_ids = sorted(placements.keys())
        for _ in range(iterations):
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    ni = node_ids[i]
                    nj = node_ids[j]
                    xi, yi, zi = placements[ni]
                    xj, yj, zj = placements[nj]
                    dx, dy, dz = xi - xj, yi - yj, zi - zj
                    dist = float(np.sqrt(dx * dx + dy * dy + dz * dz))
                    if dist <= 1e-6 or dist >= min_distance:
                        continue
                    push = (min_distance - dist) * 0.5
                    nx, ny, nz = dx / dist, dy / dist, dz / dist
                    xi, yi, zi = clamp_to_cube(xi + nx * push, yi + ny * push, zi + nz * push)
                    xj, yj, zj = clamp_to_cube(xj - nx * push, yj - ny * push, zj - nz * push)
                    placements[ni] = (round(xi, 4), round(yi, 4), round(zi, 4))
                    placements[nj] = (round(xj, 4), round(yj, 4), round(zj, 4))


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
