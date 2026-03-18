"""
SpatialSeed Spatial Prior Field (SPF) and StyleProfile, Currently using 
=======================================================
Stage 5: SPF Resolver

Responsibilities:
- Define instrument-aware spatial priors (base placement tendencies)
- Resolve (InstrumentProfile, z, MIR, tags) -> StyleProfile
- Store minimal trace for reproducibility

Per spec: DesignSpecV1.md 2.1, 3.1, agents.md 8
"""

import math
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field


# ======================================================================
# Data classes
# ======================================================================

@dataclass
class InstrumentProfile:
    """
    Base spatial prior for an instrument category.

    Per spec (DesignSpecV1.md 2.1):
    SPF is a curated, deterministic set of instrument-aware spatial priors.
    Not ML-trained in v1; purely hand-tuned.
    """
    category: str              # e.g., "vocals", "bass", "drums", etc.
    role: str                  # e.g., "lead", "rhythm", "bass", etc.

    # Base placement tendencies (spherical, later converted to Cartesian)
    base_azimuth_deg: float    # Mean azimuth in degrees (0 = front, +90 = right)
    azimuth_spread_deg: float  # How much style_vector can widen azimuth
    base_elevation_deg: float  # Mean elevation in degrees (0 = horizon, +90 = up)
    elevation_range_deg: float # How much height_usage can push elevation
    base_distance: float       # Distance from listener [0, 1]

    # Spread / diffuseness
    default_spread: float      # Default angular spread [0, 1]

    # Motion archetype defaults
    motion_archetype: str      # "static", "gentle_drift", "orbit", "reactive"

    # Modulation sensitivities (how much MIR feature couples to motion)
    energy_sensitivity: float
    flux_sensitivity: float
    brightness_sensitivity: float


@dataclass
class StyleProfile:
    """
    Resolved per-object style profile.

    Result of: SPF + z + MIR + tags -> StyleProfile
    """
    node_id: str
    category: str
    role: str

    # Resolved placement (Cartesian in normalized cube [-1,1]^3)
    base_x: float
    base_y: float
    base_z: float

    # Resolved spread
    spread: float

    # Motion parameters
    motion_intensity: float    # [0, 1]
    motion_type: str           # "static", "drift", "orbit", "reactive"

    # Modulation coupling (MIR feature name -> scaled sensitivity)
    mir_coupling: Dict[str, float] = field(default_factory=dict)

    # Minimal trace for reproducibility
    trace: Dict = field(default_factory=dict)


# ======================================================================
# Coordinate helpers
# ======================================================================

def spherical_to_cartesian(azimuth_deg: float, elevation_deg: float,
                           distance: float) -> Tuple[float, float, float]:
    """
    Convert spherical coordinates to Cartesian XYZ in the LUSID cube.

    Args:
        azimuth_deg:   Angle in degrees.  0 = front, +90 = right, -90 = left.
        elevation_deg: Angle in degrees.  0 = horizon, +90 = up, -90 = down.
        distance:      Radial distance [0, 1].

    Returns:
        (x, y, z) in normalized cube.
        +X = right, +Y = front, +Z = up  (per agents.md 2.2)
    """
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    x = distance * math.cos(el) * math.sin(az)
    y = distance * math.cos(el) * math.cos(az)
    z = distance * math.sin(el)
    return (x, y, z)


def clamp_to_cube(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Clamp to [-1, 1]^3."""
    return (
        max(-1.0, min(1.0, x)),
        max(-1.0, min(1.0, y)),
        max(-1.0, min(1.0, z)),
    )


# ======================================================================
# SPF Resolver
# ======================================================================

class SPFResolver:
    """
    Spatial Prior Field resolver.

    Maps (InstrumentProfile, z, MIR, tags) -> StyleProfile
    """

    def __init__(self, spf_config_path: Optional[str] = None):
        self.instrument_profiles: Dict[Tuple[str, str], InstrumentProfile] = {}
        if spf_config_path:
            self.load_spf_config(spf_config_path)
        else:
            self._init_default_profiles()

    # ------------------------------------------------------------------
    # Default profiles
    # ------------------------------------------------------------------

    def _init_default_profiles(self):
        """
        Curated instrument profiles.

        Convention:
        - azimuth 0 = dead centre (front).  Positive = right.
        - elevation 0 = ear level.  Positive = above.
        - distance 1.0 = far wall of cube.
        """

        # -- vocals (lead) -- front-centre, gentle drift
        self.instrument_profiles[("vocals", "lead")] = InstrumentProfile(
            category="vocals", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=15.0,
            base_elevation_deg=5.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.12,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15,
            flux_sensitivity=0.10,
            brightness_sensitivity=0.25,
        )

        # -- vocals (backing / unknown role) -- slightly wider
        self.instrument_profiles[("vocals", "unknown")] = InstrumentProfile(
            category="vocals", role="unknown",
            base_azimuth_deg=0.0, azimuth_spread_deg=35.0,
            base_elevation_deg=8.0, elevation_range_deg=15.0,
            base_distance=0.70,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15,
            flux_sensitivity=0.10,
            brightness_sensitivity=0.20,
        )

        # -- bass -- centre, low, mostly static
        self.instrument_profiles[("bass", "bass")] = InstrumentProfile(
            category="bass", role="bass",
            base_azimuth_deg=0.0, azimuth_spread_deg=10.0,
            base_elevation_deg=-5.0, elevation_range_deg=5.0,
            base_distance=0.55,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.08,
            flux_sensitivity=0.05,
            brightness_sensitivity=0.0,
        )

        # -- drums (percussion) -- wide spread, reactive
        self.instrument_profiles[("drums", "percussion")] = InstrumentProfile(
            category="drums", role="percussion",
            base_azimuth_deg=0.0, azimuth_spread_deg=50.0,
            base_elevation_deg=0.0, elevation_range_deg=20.0,
            base_distance=0.72,
            default_spread=0.22,
            motion_archetype="reactive",
            energy_sensitivity=0.35,
            flux_sensitivity=0.50,
            brightness_sensitivity=0.15,
        )

        # -- guitar (rhythm) -- off-centre, moderate drift
        self.instrument_profiles[("guitar", "rhythm")] = InstrumentProfile(
            category="guitar", role="rhythm",
            base_azimuth_deg=-25.0, azimuth_spread_deg=30.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.15,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20,
            flux_sensitivity=0.15,
            brightness_sensitivity=0.20,
        )

        # -- guitar (lead) -- slightly off-centre the other side
        self.instrument_profiles[("guitar", "lead")] = InstrumentProfile(
            category="guitar", role="lead",
            base_azimuth_deg=15.0, azimuth_spread_deg=20.0,
            base_elevation_deg=3.0, elevation_range_deg=8.0,
            base_distance=0.60,
            default_spread=0.12,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20,
            flux_sensitivity=0.15,
            brightness_sensitivity=0.25,
        )

        # -- keys (rhythm) -- slight right, ear-level
        self.instrument_profiles[("keys", "rhythm")] = InstrumentProfile(
            category="keys", role="rhythm",
            base_azimuth_deg=20.0, azimuth_spread_deg=25.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15,
            flux_sensitivity=0.10,
            brightness_sensitivity=0.20,
        )

        # -- strings (rhythm) -- wide, slightly elevated, gentle drift
        self.instrument_profiles[("strings", "rhythm")] = InstrumentProfile(
            category="strings", role="rhythm",
            base_azimuth_deg=0.0, azimuth_spread_deg=55.0,
            base_elevation_deg=10.0, elevation_range_deg=20.0,
            base_distance=0.75,
            default_spread=0.28,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20,
            flux_sensitivity=0.15,
            brightness_sensitivity=0.30,
        )

        # -- pads (rhythm / ambience) -- wide, elevated, orbit-capable
        self.instrument_profiles[("pads", "rhythm")] = InstrumentProfile(
            category="pads", role="rhythm",
            base_azimuth_deg=0.0, azimuth_spread_deg=70.0,
            base_elevation_deg=15.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.35,
            motion_archetype="orbit",
            energy_sensitivity=0.10,
            flux_sensitivity=0.05,
            brightness_sensitivity=0.15,
        )

        # -- fx -- anywhere, reactive
        self.instrument_profiles[("fx", "fx")] = InstrumentProfile(
            category="fx", role="fx",
            base_azimuth_deg=0.0, azimuth_spread_deg=90.0,
            base_elevation_deg=0.0, elevation_range_deg=30.0,
            base_distance=0.85,
            default_spread=0.30,
            motion_archetype="reactive",
            energy_sensitivity=0.40,
            flux_sensitivity=0.60,
            brightness_sensitivity=0.30,
        )

        # -- fallback "other" / "unknown" -- mid-field, static
        self.instrument_profiles[("other", "unknown")] = InstrumentProfile(
            category="other", role="unknown",
            base_azimuth_deg=0.0, azimuth_spread_deg=40.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.70,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.10,
            flux_sensitivity=0.10,
            brightness_sensitivity=0.10,
        )

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def load_spf_config(self, config_path: str):
        """Load SPF configuration from JSON."""
        with open(config_path, "r") as f:
            config = json.load(f)
        for entry in config.get("profiles", []):
            key = (entry["category"], entry["role"])
            self.instrument_profiles[key] = InstrumentProfile(**entry)

    # ------------------------------------------------------------------
    # Profile lookup with fallback chain
    # ------------------------------------------------------------------

    def get_instrument_profile(self, category: str, role: str) -> InstrumentProfile:
        """
        Lookup profile: exact (category, role) -> category-any -> fallback.
        """
        key = (category, role)
        if key in self.instrument_profiles:
            return self.instrument_profiles[key]

        # Category with any role
        for (cat, _rol), profile in self.instrument_profiles.items():
            if cat == category:
                return profile

        # Global fallback
        return self.instrument_profiles.get(
            ("other", "unknown"),
            # Ultimate safety net
            InstrumentProfile(
                category="other", role="unknown",
                base_azimuth_deg=0.0, azimuth_spread_deg=30.0,
                base_elevation_deg=0.0, elevation_range_deg=10.0,
                base_distance=0.70, default_spread=0.20,
                motion_archetype="static",
                energy_sensitivity=0.1, flux_sensitivity=0.1,
                brightness_sensitivity=0.1,
            ),
        )

    # ------------------------------------------------------------------
    # Resolve StyleProfile
    # ------------------------------------------------------------------

    def resolve_style_profile(
        self,
        node_id: str,
        classification: Dict,
        mir_features: Dict,
        style_vector: np.ndarray,
        tags: Optional[Dict] = None,
        stereo_side: Optional[str] = None,
    ) -> StyleProfile:
        """
        Resolve StyleProfile from inputs.

        Args:
            node_id:        e.g. "11.1"
            classification: {category, role_hint, ...}
            mir_features:   {spectral_centroid_mean, ...}
            style_vector:   8-dim z from SeedMatrix
            tags:           optional constraint flags
            stereo_side:    "left" or "right" for stereo-pair offset (or None)

        Returns:
            Fully resolved StyleProfile.
        """
        category = classification.get("category", "unknown")
        role = classification.get("role_hint", "unknown")

        profile = self.get_instrument_profile(category, role)

        # Unpack style vector (same order as seed_matrix.py)
        placement_spread   = float(style_vector[0])
        height_usage       = float(style_vector[1])
        motion_intensity   = float(style_vector[2])
        motion_complexity  = float(style_vector[3])
        symmetry_bias      = float(style_vector[4])
        front_back_bias    = float(style_vector[5])
        ensemble_cohesion  = float(style_vector[6])
        modulation_sens    = float(style_vector[7])

        # ----- Azimuth -----
        # Base azimuth modulated by placement_spread
        az_deg = profile.base_azimuth_deg
        az_spread = profile.azimuth_spread_deg * placement_spread
        # Apply stereo-pair offset: left channel goes negative, right goes positive
        if stereo_side == "left":
            az_deg = az_deg - az_spread * 0.5
        elif stereo_side == "right":
            az_deg = az_deg + az_spread * 0.5
        else:
            # Single object: apply small deterministic offset based on node_id hash
            # to avoid all objects stacking at the same azimuth
            nid_hash = hash(node_id) % 1000 / 1000.0  # [0, 1)
            az_deg = az_deg + az_spread * (nid_hash - 0.5)

        # ----- Elevation -----
        el_deg = profile.base_elevation_deg + profile.elevation_range_deg * height_usage

        # ----- Distance -----
        # Front-back bias: low = close/front, high = farther/surround
        dist = profile.base_distance
        dist = dist * (0.7 + 0.3 * front_back_bias)
        dist = max(0.0, min(1.0, dist))

        # ----- Convert to Cartesian -----
        bx, by, bz = spherical_to_cartesian(az_deg, el_deg, dist)
        bx, by, bz = clamp_to_cube(bx, by, bz)

        # ----- Spread -----
        spread = profile.default_spread * (0.5 + 0.5 * placement_spread)
        spread = max(0.0, min(1.0, spread))

        # ----- Motion type resolution -----
        motion_type = profile.motion_archetype
        if motion_intensity < 0.10:
            motion_type = "static"
        elif motion_type == "orbit" and motion_intensity < 0.40:
            motion_type = "gentle_drift"
        elif motion_type == "reactive" and motion_intensity < 0.25:
            motion_type = "gentle_drift"

        # ----- MIR coupling -----
        mir_coupling = {
            "energy": profile.energy_sensitivity * modulation_sens,
            "flux": profile.flux_sensitivity * modulation_sens,
            "brightness": profile.brightness_sensitivity * modulation_sens,
        }

        # ----- Trace -----
        trace = {
            "profile_key": [category, role],
            "z_snapshot": style_vector.tolist(),
            "azimuth_deg": round(az_deg, 2),
            "elevation_deg": round(el_deg, 2),
            "distance": round(dist, 3),
            "stereo_side": stereo_side,
        }
        if tags:
            trace["tags"] = tags

        return StyleProfile(
            node_id=node_id,
            category=category,
            role=role,
            base_x=round(bx, 4),
            base_y=round(by, 4),
            base_z=round(bz, 4),
            spread=round(spread, 4),
            motion_intensity=round(motion_intensity, 4),
            motion_type=motion_type,
            mir_coupling=mir_coupling,
            trace=trace,
        )

    # ------------------------------------------------------------------
    # Batch resolve
    # ------------------------------------------------------------------

    def resolve_all_profiles(
        self,
        manifest: Dict,
        classifications: Dict,
        mir_summary: Dict,
        style_vector: np.ndarray,
    ) -> Dict[str, StyleProfile]:
        """
        Resolve StyleProfiles for all nodes.

        Uses the manifest to determine stereo pairing so that L/R channels
        are offset symmetrically.
        """
        print("Stage 5: SPF Resolution -> StyleProfile")

        # Build a map: node_id -> stereo_side
        stereo_map: Dict[str, Optional[str]] = {}
        for stem in manifest.get("stems", []):
            nids = stem.get("node_ids", [])
            if stem.get("channels", 1) == 2 and len(nids) == 2:
                stereo_map[nids[0]] = "left"
                stereo_map[nids[1]] = "right"
            else:
                for nid in nids:
                    stereo_map[nid] = None

        profiles: Dict[str, StyleProfile] = {}
        for node_id, classification in sorted(classifications.items()):
            mir_features = mir_summary.get("stems", {}).get(node_id, {}).get("features", {})
            side = stereo_map.get(node_id)

            sp = self.resolve_style_profile(
                node_id=node_id,
                classification=classification,
                mir_features=mir_features,
                style_vector=style_vector,
                stereo_side=side,
            )
            profiles[node_id] = sp
            print(
                f"  {node_id}: {sp.category}/{sp.role}  "
                f"pos=({sp.base_x:.3f}, {sp.base_y:.3f}, {sp.base_z:.3f})  "
                f"motion={sp.motion_type}  spread={sp.spread:.3f}"
            )

        return profiles

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_profiles(self, profiles: Dict[str, StyleProfile], output_path: str):
        """Save resolved StyleProfiles to JSON."""
        from pathlib import Path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        profiles_dict = {
            nid: asdict(prof) for nid, prof in profiles.items()
        }
        with open(output_path, "w") as f:
            json.dump(profiles_dict, f, indent=2)
        print(f"  Profiles saved to {output_path}")
