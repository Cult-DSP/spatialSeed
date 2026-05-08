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

import json
import math
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from src.spatial.spf import StyleProfile, clamp_to_cube

logger = logging.getLogger("spatialSeed.placement")

# Clamp severity thresholds
_CLAMP_WARN_COUNT = 3       # warn if this many or more clamp events occur
_CLAMP_SEVERE_DELTA = 0.3   # per-axis delta this large is flagged as severe


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
        # Additive Y bias per category after front/back transform.
        # Positive = pushed forward; negative = pushed rearward.
        self.category_front_bias = {
            "vocals": 0.12,
            "bass": 0.00,
            "drums": 0.05,
            "percussion": 0.03,
            "guitar": 0.03,
            "keys": 0.05,
            "strings": 0.03,
            "pads": -0.05,
            "fx": -0.10,
            "ambience": -0.15,
            "sound_design": -0.12,
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
    # Pair metadata
    # ------------------------------------------------------------------

    @staticmethod
    def build_stereo_pairs(manifest: Optional[Dict]) -> Dict[str, str]:
        """
        Extract L->R stereo pair mapping from session manifest.

        Returns:
            {left_node_id: right_node_id} for all stereo stems.
        """
        pairs: Dict[str, str] = {}
        if not manifest:
            return pairs
        for stem in manifest.get("stems", []):
            node_ids = stem.get("node_ids", [])
            if len(node_ids) == 2:
                pairs[node_ids[0]] = node_ids[1]
        return pairs

    # ------------------------------------------------------------------
    # MIR depth bias
    # ------------------------------------------------------------------

    @staticmethod
    def compute_mir_depth_bias(node_id: str, mir_summary: Optional[Dict],
                               max_bias: float = 0.12) -> float:
        """
        Derive a Y (depth) bias from MIR loudness and spectral brightness.

        Louder and brighter sources bias forward (+Y); softer and darker
        sources bias rearward (-Y). Returns a value in [-max_bias, +max_bias].
        """
        if not mir_summary:
            return 0.0
        features = mir_summary.get(node_id, {})
        if not features:
            return 0.0

        rms_db = features.get("rms_energy", -60.0)
        centroid = features.get("spectral_centroid_mean", 2000.0)

        # Normalize to [0, 1]: -60 dB = 0 (soft), -20 dB = 1 (loud)
        loudness_norm = float(np.clip((rms_db + 60.0) / 40.0, 0.0, 1.0))
        # Normalize centroid: 500 Hz = 0 (dark), 6000 Hz = 1 (bright)
        bright_norm = float(np.clip((centroid - 500.0) / 5500.0, 0.0, 1.0))

        # Combined score: 0.5 → neutral, 1.0 → forward, 0.0 → rearward
        score = 0.5 * loudness_norm + 0.5 * bright_norm
        return (score - 0.5) * 2.0 * max_bias

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

    def apply_category_front_curve(self, y: float, category: str) -> float:
        """
        Apply a category-specific additive Y bias for front/rear placement.

        Vocals/keys push forward; FX/ambience push rearward.  The bias is
        scaled so it remains small relative to the full cube range.
        """
        bias = self.category_front_bias.get(category, 0.0)
        return y + bias

    # ------------------------------------------------------------------
    # Single placement
    # ------------------------------------------------------------------

    def compute_placement(
        self,
        profile: StyleProfile,
        style_vector: np.ndarray,
        no_height: bool = False,
        mir_depth_bias: float = 0.0,
    ) -> Tuple[float, float, float]:
        """
        Compute static placement for a single object.

        Pipeline:
        1. Spread + cohesion + symmetry (XY)
        2. Height banding
        3. Height scaling
        4. Distance scaling
        5. Front/back bias (Seed Matrix z[5])
        6. Category-specific front curve
        7. MIR depth bias (loudness/brightness)
        8. Clamp to cube
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
            x, y, z,
            placement_spread=placement_spread,
            ensemble_cohesion=ensemble_cohesion,
            category=profile.category,
            role=profile.role,
        )
        y = self.apply_front_back_bias(y, front_back_bias)
        y = self.apply_category_front_curve(y, profile.category)
        y = float(np.clip(y + mir_depth_bias, -1.0, 1.0))

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
        mir_summary: Optional[Dict] = None,
        manifest: Optional[Dict] = None,
        work_dir: Optional[str] = None,
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Compute static placements for all objects.

        Args:
            profiles: Per-node StyleProfile map.
            style_vector: Seed Matrix style vector.
            no_height: If True, force all z=0.
            mir_summary: MIR feature dict keyed by node_id (used for depth bias).
            manifest: Session manifest (used to extract stereo pair info).
            work_dir: If provided, write placement_audit.json here.

        Returns:
            Dict of {node_id: (x, y, z)}
        """
        print("Stage 6: Static Placement")

        stereo_pairs = self.build_stereo_pairs(manifest)
        placements: Dict[str, Tuple[float, float, float]] = {}

        for node_id in sorted(profiles.keys()):
            profile = profiles[node_id]
            mir_bias = self.compute_mir_depth_bias(node_id, mir_summary)
            pos = self.compute_placement(profile, style_vector, no_height,
                                         mir_depth_bias=mir_bias)
            placements[node_id] = pos
            print(f"  {node_id}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")

        self.apply_front_zone_density(placements, profiles, style_vector)

        if stereo_pairs:
            self.apply_stereo_pair_cohesion(placements, stereo_pairs)

        ensemble_cohesion = self._safe_z(style_vector, 6, 0.5)
        min_dist = self._dynamic_min_distance(len(placements), ensemble_cohesion)
        self.apply_inter_object_spacing(placements, profiles, min_distance=min_dist)

        self.apply_scene_centroid_normalization(placements)

        self._report_clamp_severity()

        if work_dir:
            self.write_placement_audit(placements, work_dir)

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

    def apply_stereo_pair_cohesion(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        stereo_pairs: Dict[str, str],
        min_x_separation: float = 0.15,
    ) -> None:
        """
        Enforce shared Y/Z and minimum X separation for L/R stereo pairs.

        Averages Y and Z so both channels sit at the same depth and height,
        then ensures a minimum horizontal spread between the two channels.
        """
        for left_id, right_id in stereo_pairs.items():
            if left_id not in placements or right_id not in placements:
                continue

            lx, ly, lz = placements[left_id]
            rx, ry, rz = placements[right_id]

            shared_y = (ly + ry) / 2.0
            shared_z = (lz + rz) / 2.0

            x_sep = abs(lx - rx)
            if x_sep < min_x_separation:
                half = min_x_separation / 2.0
                lx = min(lx, -half) if lx <= 0 else lx - half
                rx = max(rx, half) if rx >= 0 else rx + half

            placements[left_id] = clamp_to_cube(round(lx, 4), round(shared_y, 4),
                                                 round(shared_z, 4))
            placements[right_id] = clamp_to_cube(round(rx, 4), round(shared_y, 4),
                                                  round(shared_z, 4))

    def apply_scene_centroid_normalization(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        target: Tuple[float, float, float] = (0.0, 0.4, 0.0),
        strength: float = 0.5,
    ) -> None:
        """
        Shift all placements so the scene centroid moves toward `target`.

        Uses partial correction (strength=0.5 by default) to avoid
        over-constraining individual positions.
        """
        if not placements:
            return

        xs = [p[0] for p in placements.values()]
        ys = [p[1] for p in placements.values()]
        zs = [p[2] for p in placements.values()]

        cx, cy, cz = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
        dx = (target[0] - cx) * strength
        dy = (target[1] - cy) * strength
        dz = (target[2] - cz) * strength

        if abs(dx) < 1e-4 and abs(dy) < 1e-4 and abs(dz) < 1e-4:
            return

        for node_id, (x, y, z) in placements.items():
            placements[node_id] = clamp_to_cube(
                round(x + dx, 4), round(y + dy, 4), round(z + dz, 4)
            )

        logger.debug(
            "Centroid normalization: was (%.3f, %.3f, %.3f), shift (%.3f, %.3f, %.3f)",
            cx, cy, cz, dx, dy, dz,
        )

    @staticmethod
    def _dynamic_min_distance(n_objects: int, ensemble_cohesion: float) -> float:
        """
        Compute min_distance for spacing pass based on scene density and cohesion.

        More objects or higher cohesion (which clusters them) increases the
        threshold to keep placements audibly distinct.
        """
        density_factor = min(n_objects / 20.0, 1.5)
        return max(0.06, 0.08 * (1.0 + 0.5 * density_factor + 0.2 * ensemble_cohesion))

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
    # Clamp diagnostics
    # ------------------------------------------------------------------

    def _report_clamp_severity(self) -> None:
        """
        Emit structured warnings for clamp events.

        Warns if total clamp count exceeds _CLAMP_WARN_COUNT or if any
        single axis was clamped by more than _CLAMP_SEVERE_DELTA.
        """
        if not self.clamp_log:
            return

        n = len(self.clamp_log)
        if n >= _CLAMP_WARN_COUNT:
            logger.warning("Placement: %d positions clamped to cube (threshold=%d)",
                           n, _CLAMP_WARN_COUNT)

        for evt in self.clamp_log:
            ox, oy, oz = evt["original"]
            cx, cy, cz = evt["clamped"]
            max_delta = max(abs(ox - cx), abs(oy - cy), abs(oz - cz))
            if max_delta >= _CLAMP_SEVERE_DELTA:
                logger.warning(
                    "Severe clamp for %s: delta=%.3f  %s -> %s",
                    evt["node_id"], max_delta, evt["original"], evt["clamped"],
                )
            else:
                logger.debug("Clamp %s: %s -> %s", evt["node_id"],
                             evt["original"], evt["clamped"])

    # ------------------------------------------------------------------
    # Placement audit
    # ------------------------------------------------------------------

    def write_placement_audit(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        work_dir: str,
        min_distance: float = 0.08,
    ) -> None:
        """
        Write a JSON summary of placement statistics to work/placement_audit.json.

        Fields: per-axis min/max/mean, crowded pair count, clamp count.
        """
        if not placements:
            return

        xs = [p[0] for p in placements.values()]
        ys = [p[1] for p in placements.values()]
        zs = [p[2] for p in placements.values()]

        node_ids = sorted(placements.keys())
        crowded = 0
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                pi = placements[node_ids[i]]
                pj = placements[node_ids[j]]
                d = math.sqrt(sum((a - b) ** 2 for a, b in zip(pi, pj)))
                if d < min_distance:
                    crowded += 1

        audit = {
            "object_count": len(placements),
            "x": {"min": round(min(xs), 4), "max": round(max(xs), 4),
                  "mean": round(sum(xs) / len(xs), 4)},
            "y": {"min": round(min(ys), 4), "max": round(max(ys), 4),
                  "mean": round(sum(ys) / len(ys), 4)},
            "z": {"min": round(min(zs), 4), "max": round(max(zs), 4),
                  "mean": round(sum(zs) / len(zs), 4)},
            "crowded_pairs": crowded,
            "clamped_count": len(self.clamp_log),
        }

        out_path = Path(work_dir) / "placement_audit.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(audit, f, indent=2)
        logger.info("Placement audit written to %s", out_path)


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

    avg_y = (ly + ry) / 2.0
    avg_z = (lz + rz) / 2.0

    return (
        clamp_to_cube(lx, avg_y, avg_z),
        clamp_to_cube(rx, avg_y, avg_z),
    )
