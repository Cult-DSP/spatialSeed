"""
SpatialSeed Spatial Prior Field (SPF) and StyleProfile
=======================================================
Stage 5: SPF Resolver

Responsibilities:
- Define instrument-aware spatial priors (base placement tendencies)
- Resolve (InstrumentProfile, z, MIR, tags) → StyleProfile
- Store minimal trace for reproducibility

Per spec: DesignSpecV1.md § 2.1, 3.1, agents.md § 8
"""

import numpy as np
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class InstrumentProfile:
    """
    Base spatial prior for an instrument category.
    
    Per spec (DesignSpecV1.md § 2.1):
    SPF is a curated, deterministic set of instrument-aware spatial priors.
    """
    category: str  # e.g., "vocals", "bass", "drums", etc.
    role: str  # e.g., "lead", "rhythm", "bass", etc.
    
    # Base placement tendencies (normalized XYZ)
    base_azimuth_mean: float  # Mean azimuth in radians
    base_azimuth_std: float   # Std dev of azimuth
    base_elevation_mean: float  # Mean elevation in radians
    base_elevation_std: float   # Std dev of elevation
    base_distance_mean: float  # Mean distance [0,1]
    base_distance_std: float   # Std dev of distance
    
    # Spread/diffuseness preferences
    default_spread: float  # Default angular spread
    
    # Motion archetype defaults
    motion_archetype: str  # "static", "gentle_drift", "orbit", "reactive", etc.
    
    # Modulation sensitivities (MIR feature → motion coupling)
    energy_sensitivity: float  # How much loudness affects motion
    flux_sensitivity: float    # How much spectral flux affects motion
    brightness_sensitivity: float  # How much centroid affects motion


@dataclass
class StyleProfile:
    """
    Resolved per-object style profile.
    
    Result of: SPF + z + MIR + tags → StyleProfile
    """
    node_id: str
    category: str
    role: str
    
    # Resolved placement (base XYZ in normalized cube)
    base_x: float
    base_y: float
    base_z: float
    
    # Resolved spread
    spread: float
    
    # Motion parameters
    motion_intensity: float  # [0,1]
    motion_type: str  # "static", "drift", "orbit", "reactive", etc.
    
    # Modulation coupling
    mir_coupling: Dict[str, float]  # Maps MIR feature → motion sensitivity
    
    # Minimal trace (for reproducibility)
    trace: Dict


class SPFResolver:
    """
    Spatial Prior Field resolver.
    
    Maps (InstrumentProfile, z, MIR, tags) → StyleProfile
    """
    
    def __init__(self, spf_config_path: Optional[str] = None):
        """
        Initialize SPF resolver.
        
        Args:
            spf_config_path: Optional path to SPF configuration JSON
        """
        self.instrument_profiles = {}
        
        if spf_config_path:
            self.load_spf_config(spf_config_path)
        else:
            self.init_default_profiles()
    
    def init_default_profiles(self):
        """
        Initialize default instrument profiles.
        
        Per spec (DesignSpecV1.md § 2.1):
        - Base placement tendencies translated to normalized XYZ
        - Not ML-trained in v1; curated and deterministic
        """
        # TODO: Define profiles for each category × role combination
        # Example profiles:
        
        # Vocals (lead)
        self.instrument_profiles[("vocals", "lead")] = InstrumentProfile(
            category="vocals",
            role="lead",
            base_azimuth_mean=0.0,  # Center front
            base_azimuth_std=0.1,
            base_elevation_mean=0.0,  # Ear level
            base_elevation_std=0.05,
            base_distance_mean=0.6,  # Mid-distance
            base_distance_std=0.1,
            default_spread=0.15,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.2,
            flux_sensitivity=0.1,
            brightness_sensitivity=0.3,
        )
        
        # Bass (bass role)
        self.instrument_profiles[("bass", "bass")] = InstrumentProfile(
            category="bass",
            role="bass",
            base_azimuth_mean=0.0,  # Center
            base_azimuth_std=0.2,
            base_elevation_mean=-0.2,  # Slightly low
            base_elevation_std=0.05,
            base_distance_mean=0.5,
            base_distance_std=0.1,
            default_spread=0.2,
            motion_archetype="static",
            energy_sensitivity=0.1,
            flux_sensitivity=0.05,
            brightness_sensitivity=0.0,
        )
        
        # Drums (percussion)
        self.instrument_profiles[("drums", "percussion")] = InstrumentProfile(
            category="drums",
            role="percussion",
            base_azimuth_mean=0.0,
            base_azimuth_std=0.5,  # Wide spread
            base_elevation_mean=0.0,
            base_elevation_std=0.2,
            base_distance_mean=0.7,
            base_distance_std=0.15,
            default_spread=0.25,
            motion_archetype="reactive",
            energy_sensitivity=0.4,
            flux_sensitivity=0.6,
            brightness_sensitivity=0.2,
        )
        
        # TODO: Add profiles for:
        # - guitar (lead, rhythm)
        # - keys (lead, rhythm)
        # - pads (ambience)
        # - fx (ambience)
        # - other (unknown)
    
    def load_spf_config(self, config_path: str):
        """
        Load SPF configuration from JSON.
        
        Args:
            config_path: Path to SPF config JSON
        """
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # TODO: Parse config and populate instrument_profiles
        pass
    
    def get_instrument_profile(self, category: str, role: str) -> InstrumentProfile:
        """
        Get instrument profile for category × role.
        
        Args:
            category: Instrument category
            role: Role hint
            
        Returns:
            InstrumentProfile (with fallbacks)
        """
        # Try exact match
        key = (category, role)
        if key in self.instrument_profiles:
            return self.instrument_profiles[key]
        
        # Try category with any role
        for (cat, rol), profile in self.instrument_profiles.items():
            if cat == category:
                return profile
        
        # Fallback to "other" or default
        # TODO: Define fallback profile
        return self.instrument_profiles.get(
            ("other", "unknown"),
            InstrumentProfile(
                category="other", role="unknown",
                base_azimuth_mean=0.0, base_azimuth_std=0.3,
                base_elevation_mean=0.0, base_elevation_std=0.2,
                base_distance_mean=0.7, base_distance_std=0.1,
                default_spread=0.2, motion_archetype="static",
                energy_sensitivity=0.1, flux_sensitivity=0.1,
                brightness_sensitivity=0.1,
            )
        )
    
    def resolve_style_profile(self, node_id: str, 
                             classification: Dict,
                             mir_features: Dict,
                             style_vector: np.ndarray,
                             tags: Optional[Dict] = None) -> StyleProfile:
        """
        Resolve StyleProfile from inputs.
        
        Args:
            node_id: Node ID (e.g., "11.1")
            classification: Classification result dict
            mir_features: MIR features dict
            style_vector: Style vector z from Seed Matrix
            tags: Optional additional tags/constraints
            
        Returns:
            Resolved StyleProfile
            
        Per spec (agents.md § 8):
        - (InstrumentProfile, z, MIR, tags) → StyleProfile
        - Store minimal trace
        """
        category = classification["category"]
        role = classification["role_hint"]
        
        # Get base instrument profile
        profile = self.get_instrument_profile(category, role)
        
        # Extract style vector components
        placement_spread = style_vector[0]
        height_usage = style_vector[1]
        motion_intensity = style_vector[2]
        motion_complexity = style_vector[3]
        symmetry_bias = style_vector[4]
        front_back_bias = style_vector[5]
        ensemble_cohesion = style_vector[6]
        modulation_sensitivity = style_vector[7]
        
        # TODO: Resolve base XYZ placement
        # - Sample from profile's azimuth/elevation/distance distributions
        # - Modulate by style_vector components
        # - Apply constraints (symmetry, front-back bias, etc.)
        # - Convert spherical → Cartesian XYZ
        
        # Placeholder placement
        base_x = 0.0
        base_y = 0.5
        base_z = 0.0
        
        # TODO: Resolve spread
        spread = profile.default_spread * (0.5 + 0.5 * placement_spread)
        
        # TODO: Resolve motion parameters
        motion_type = profile.motion_archetype
        if motion_intensity < 0.1:
            motion_type = "static"
        elif motion_intensity > 0.7 and motion_complexity > 0.5:
            motion_type = "orbit"
        
        # TODO: Build MIR coupling dict
        mir_coupling = {
            "energy": profile.energy_sensitivity * modulation_sensitivity,
            "flux": profile.flux_sensitivity * modulation_sensitivity,
            "brightness": profile.brightness_sensitivity * modulation_sensitivity,
        }
        
        # Minimal trace
        trace = {
            "profile_key": (category, role),
            "z_snapshot": style_vector.tolist(),
            "constraints": tags if tags else {},
        }
        
        return StyleProfile(
            node_id=node_id,
            category=category,
            role=role,
            base_x=base_x,
            base_y=base_y,
            base_z=base_z,
            spread=spread,
            motion_intensity=motion_intensity,
            motion_type=motion_type,
            mir_coupling=mir_coupling,
            trace=trace,
        )
    
    def resolve_all_profiles(self, classifications: Dict,
                            mir_summary: Dict,
                            style_vector: np.ndarray) -> Dict[str, StyleProfile]:
        """
        Resolve StyleProfiles for all nodes.
        
        Args:
            classifications: Dict of classification results keyed by node_id
            mir_summary: MIR summary dict
            style_vector: Style vector z from Seed Matrix
            
        Returns:
            Dict of StyleProfiles keyed by node_id
        """
        print("Stage 5: SPF Resolution → StyleProfile")
        
        profiles = {}
        
        for node_id, classification in classifications.items():
            mir_features = mir_summary["stems"].get(node_id, {}).get("features", {})
            
            profile = self.resolve_style_profile(
                node_id=node_id,
                classification=classification,
                mir_features=mir_features,
                style_vector=style_vector,
            )
            
            profiles[node_id] = profile
            print(f"  {node_id}: {profile.category}/{profile.role} at ({profile.base_x:.2f}, {profile.base_y:.2f}, {profile.base_z:.2f})")
        
        return profiles
    
    def save_profiles(self, profiles: Dict[str, StyleProfile], output_path: str):
        """
        Save resolved StyleProfiles to JSON.
        
        Args:
            profiles: Dict of StyleProfiles
            output_path: Path to write profiles JSON
        """
        profiles_dict = {
            node_id: asdict(profile)
            for node_id, profile in profiles.items()
        }
        
        with open(output_path, 'w') as f:
            json.dump(profiles_dict, f, indent=2)


def spherical_to_cartesian(azimuth: float, elevation: float, distance: float) -> tuple:
    """
    Convert spherical coordinates to Cartesian XYZ.
    
    Args:
        azimuth: Azimuth angle in radians (0 = front, +π/2 = right)
        elevation: Elevation angle in radians (0 = horizon, +π/2 = up)
        distance: Distance [0,1]
        
    Returns:
        Tuple of (x, y, z) in normalized cube [-1,1]³
        
    Per spec (agents.md § 2.2):
    - +X = right, +Y = front, +Z = up
    """
    # TODO: Implement conversion
    # x = distance * cos(elevation) * sin(azimuth)
    # y = distance * cos(elevation) * cos(azimuth)
    # z = distance * sin(elevation)
    
    x = 0.0
    y = 0.0
    z = 0.0
    
    return (x, y, z)
