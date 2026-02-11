"""
SpatialSeed Gesture Engine
===========================
Stage 7: Gesture Generation (Sparse Keyframes)

Responsibilities:
- Generate sparse keyframes for object motion
- Emit delta frames (only nodes that changed)
- Ensure t=0.0 keyframe for each source
- Motion intensity governed by Seed Matrix v axis

Per spec: lowLevelSpecsV1.md 0, 3.2, agents.md 8
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from src.spf import StyleProfile, clamp_to_cube


@dataclass
class Keyframe:
    """Spatial keyframe for an object."""
    time: float              # Time in seconds
    x: float
    y: float
    z: float
    spread: Optional[float] = None


class GestureEngine:
    """
    Generates sparse spatial keyframes for object motion.

    Per spec (lowLevelSpecsV1.md 0):
    - Motion is sparse keyframes only (no dense sampling).
    - Emit delta frames: only nodes that changed.
    - Ensure t=0.0 keyframe for each source.
    """

    # Keyframe emission thresholds (per agents.md 13)
    POS_EPSILON = 0.01       # Position change threshold (normalised units)
    SPREAD_EPSILON = 0.02    # Spread change threshold

    def __init__(self, duration_seconds: float):
        self.duration = duration_seconds
        self.keyframes: Dict[str, List[Keyframe]] = {}

    # ------------------------------------------------------------------
    # Motion generators
    # ------------------------------------------------------------------

    def generate_static_gesture(
        self, node_id: str,
        x: float, y: float, z: float,
        spread: float,
    ) -> List[Keyframe]:
        """Single keyframe at t=0 (no motion)."""
        return [Keyframe(time=0.0, x=x, y=y, z=z, spread=spread)]

    def generate_drift_gesture(
        self, node_id: str,
        start_pos: Tuple[float, float, float],
        spread: float,
        profile: StyleProfile,
        mir_features: Dict,
    ) -> List[Keyframe]:
        """
        Gentle drift: slow, smooth motion around the base position.

        Keyframes at regular intervals with small sinusoidal offsets.
        The amplitude is scaled by motion_intensity and MIR coupling.
        """
        x0, y0, z0 = start_pos
        intensity = profile.motion_intensity
        energy_coup = profile.mir_coupling.get("energy", 0.0)
        flux_coup = profile.mir_coupling.get("flux", 0.0)

        # Amplitude: base 0.05, scaled up by intensity (max ~0.15)
        amp = 0.05 + 0.10 * intensity

        # MIR modulation: if the stem has high spectral flux, add extra drift
        stem_flux = mir_features.get("spectral_flux_mean", 0.0)
        amp += flux_coup * min(stem_flux, 1.0) * 0.05

        # Period (seconds per full oscillation cycle)
        period = max(4.0, 16.0 * (1.0 - intensity))

        # Deterministic phase offset per node
        phase = (hash(node_id) % 1000) / 1000.0 * 2.0 * math.pi

        keyframes: List[Keyframe] = []
        # Sample interval: one keyframe every ~2-4 seconds
        interval = max(2.0, period / 4.0)
        t = 0.0
        while t <= self.duration:
            angle = 2.0 * math.pi * (t / period) + phase
            dx = amp * math.sin(angle)
            dy = amp * 0.5 * math.cos(angle * 0.7)  # slower Y wobble
            dz = 0.0  # drift is horizontal only

            xk, yk, zk = clamp_to_cube(x0 + dx, y0 + dy, z0 + dz)
            keyframes.append(Keyframe(time=round(t, 3), x=xk, y=yk, z=zk, spread=spread))
            t += interval

        # Ensure final keyframe at duration if not already there
        if keyframes[-1].time < self.duration:
            xk, yk, zk = clamp_to_cube(x0, y0, z0)
            keyframes.append(Keyframe(time=round(self.duration, 3), x=xk, y=yk, z=zk, spread=spread))

        return self._apply_emission_threshold(keyframes)

    def generate_orbit_gesture(
        self, node_id: str,
        center_pos: Tuple[float, float, float],
        spread: float,
        profile: StyleProfile,
        mir_features: Dict,
    ) -> List[Keyframe]:
        """
        Orbital motion: elliptical path around centre position.

        Radius and speed scale with motion_intensity.
        """
        cx, cy, cz = center_pos
        intensity = profile.motion_intensity

        # Orbit radius: 0.1 .. 0.35
        radius = 0.10 + 0.25 * intensity

        # Orbit period: faster at high intensity (6s .. 16s)
        period = max(6.0, 16.0 * (1.0 - intensity))

        # Phase offset per node
        phase = (hash(node_id) % 1000) / 1000.0 * 2.0 * math.pi

        # Elliptical: X-radius = radius, Y-radius = radius * 0.6
        ry = radius * 0.6

        keyframes: List[Keyframe] = []
        # Sample at ~8 points per orbit
        samples_per_orbit = 8
        interval = period / samples_per_orbit
        t = 0.0
        while t <= self.duration:
            angle = 2.0 * math.pi * (t / period) + phase
            dx = radius * math.cos(angle)
            dy = ry * math.sin(angle)

            xk, yk, zk = clamp_to_cube(cx + dx, cy + dy, cz)
            keyframes.append(Keyframe(time=round(t, 3), x=xk, y=yk, z=zk, spread=spread))
            t += interval

        return self._apply_emission_threshold(keyframes)

    def generate_reactive_gesture(
        self, node_id: str,
        base_pos: Tuple[float, float, float],
        spread: float,
        profile: StyleProfile,
        mir_features: Dict,
    ) -> List[Keyframe]:
        """
        Reactive motion: position and spread coupled to MIR features.

        In v1 we use global stem features (not time-series) so reactive
        motion is approximated: high-energy / high-flux stems get more
        micro-bursts of motion (random jitter keyframes) while low-energy
        stems stay closer to static.
        """
        x0, y0, z0 = base_pos
        intensity = profile.motion_intensity
        energy_coup = profile.mir_coupling.get("energy", 0.0)

        onset_density = mir_features.get("onset_density", 0.0)
        stem_flux = mir_features.get("spectral_flux_mean", 0.0)

        # Number of reactive "bursts": more onsets -> more keyframes
        n_bursts = max(1, int(min(onset_density * intensity * 2, 20)))

        # Jitter amplitude
        jitter = 0.03 + 0.12 * intensity + energy_coup * 0.05

        # Deterministic RNG per node
        rng = np.random.RandomState(hash(node_id) % (2**31))

        keyframes: List[Keyframe] = []
        # Always start at base
        keyframes.append(Keyframe(time=0.0, x=x0, y=y0, z=z0, spread=spread))

        # Distribute bursts across duration
        burst_times = sorted(rng.uniform(0.5, self.duration - 0.5, size=n_bursts))
        for bt in burst_times:
            dx = rng.uniform(-jitter, jitter)
            dy = rng.uniform(-jitter, jitter)
            dz = rng.uniform(-jitter * 0.3, jitter * 0.3)
            xk, yk, zk = clamp_to_cube(x0 + dx, y0 + dy, z0 + dz)
            # Spread also reacts: slightly wider on bursts
            sp = min(1.0, spread + rng.uniform(0, 0.05 * intensity))
            keyframes.append(Keyframe(time=round(float(bt), 3), x=xk, y=yk, z=zk, spread=round(sp, 4)))

        # Return to base at end
        keyframes.append(Keyframe(time=round(self.duration, 3), x=x0, y=y0, z=z0, spread=spread))

        return self._apply_emission_threshold(keyframes)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def generate_gesture(
        self, node_id: str,
        placement: Tuple[float, float, float],
        profile: StyleProfile,
        mir_features: Dict,
    ) -> List[Keyframe]:
        """Generate gesture for a single object based on its motion type."""
        motion_type = profile.motion_type
        spread = profile.spread

        if profile.motion_intensity < 0.05 or motion_type == "static":
            return self.generate_static_gesture(node_id, *placement, spread)

        if motion_type in ("gentle_drift", "drift"):
            return self.generate_drift_gesture(node_id, placement, spread, profile, mir_features)

        if motion_type == "orbit":
            return self.generate_orbit_gesture(node_id, placement, spread, profile, mir_features)

        if motion_type == "reactive":
            return self.generate_reactive_gesture(node_id, placement, spread, profile, mir_features)

        # Fallback: static
        return self.generate_static_gesture(node_id, *placement, spread)

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    def generate_all_gestures(
        self,
        placements: Dict[str, Tuple[float, float, float]],
        profiles: Dict[str, StyleProfile],
        mir_summary: Dict,
    ) -> Dict[str, List[Keyframe]]:
        """Generate gestures for all objects."""
        print("Stage 7: Gesture Generation (Sparse Keyframes)")

        for node_id in sorted(placements.keys()):
            placement = placements[node_id]
            profile = profiles[node_id]
            mir_features = mir_summary.get("stems", {}).get(node_id, {}).get("features", {})

            kfs = self.generate_gesture(node_id, placement, profile, mir_features)
            self.keyframes[node_id] = kfs

            print(f"  {node_id}: {len(kfs)} keyframes ({profile.motion_type})")

        return self.keyframes

    # ------------------------------------------------------------------
    # Emission threshold filter
    # ------------------------------------------------------------------

    def _apply_emission_threshold(self, keyframes: List[Keyframe]) -> List[Keyframe]:
        """
        Remove redundant keyframes whose position delta is below POS_EPSILON.

        Always keeps the first (t=0) and last keyframe.
        """
        if len(keyframes) <= 2:
            return keyframes

        filtered = [keyframes[0]]
        for kf in keyframes[1:-1]:
            prev = filtered[-1]
            dx = abs(kf.x - prev.x)
            dy = abs(kf.y - prev.y)
            dz = abs(kf.z - prev.z)
            ds = abs((kf.spread or 0) - (prev.spread or 0))
            if max(dx, dy, dz) >= self.POS_EPSILON or ds >= self.SPREAD_EPSILON:
                filtered.append(kf)
        filtered.append(keyframes[-1])
        return filtered

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_keyframe_stats(self) -> Dict:
        """Get statistics about generated keyframes."""
        total_kf = sum(len(kfs) for kfs in self.keyframes.values())
        static_obj = sum(1 for kfs in self.keyframes.values() if len(kfs) == 1)
        n_obj = len(self.keyframes) or 1
        return {
            "total_objects": len(self.keyframes),
            "total_keyframes": total_kf,
            "static_objects": static_obj,
            "animated_objects": len(self.keyframes) - static_obj,
            "avg_keyframes_per_object": round(total_kf / n_obj, 1),
        }


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def interpolate_keyframes(kf1: Keyframe, kf2: Keyframe, alpha: float) -> Keyframe:
    """Linearly interpolate between two keyframes (for preview / debug)."""
    t = (1 - alpha) * kf1.time + alpha * kf2.time
    x = (1 - alpha) * kf1.x + alpha * kf2.x
    y = (1 - alpha) * kf1.y + alpha * kf2.y
    z = (1 - alpha) * kf1.z + alpha * kf2.z

    spread = None
    if kf1.spread is not None and kf2.spread is not None:
        spread = (1 - alpha) * kf1.spread + alpha * kf2.spread

    return Keyframe(time=t, x=x, y=y, z=z, spread=spread)
