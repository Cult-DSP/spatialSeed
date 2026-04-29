"""
SpatialSeed Spatial Prior Field (SPF) and StyleProfile, Currently using 
=======================================================
Stage 5: SPF Resolver

Responsibilities:
- Define instrument-aware spatial priors (base placement tendencies)
- Resolve (InstrumentProfile, z, MIR, tags) -> StyleProfile
- Store minimal trace for reproducibility

Per spec: DesignSpecV1.md 2.1, 3.1, agents.md 8

Data Sheet Integration (v2.1):
- Loads data from src/spfData/*.json (spfDataSheetA.json, spfDataTemplate.json)
- Generates variants for stereo instruments (hi-hats, toms, etc.)
- Enriches profiles with sheet-based source citations
"""

import math
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path


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

    # Reference citation for the spatial prior
    source_citation: Optional[str] = None


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
# Data Sheet Loaders (v2.1)
# ======================================================================

def load_spf_data_sheets():
    """
    Load and merge SPF data from JSON sheets.
    
    Returns:
        list of dicts with keys: instrument, group, role, az, el, dist, 
        source_name, source_url, publication_year, attribution, license_type
    """
    sheets = []
    sheet_dir = Path(__file__).parent.parent / "spfData"
    
    if not sheet_dir.exists():
        return sheets
    
    # Load spfDataSheetA.json (primary - drum kit, stereo variants)
    sheet_a_path = sheet_dir / "spfDataSheetA.json"
    if sheet_a_path.exists():
        try:
            with open(sheet_a_path, "r") as f:
                data = json.load(f)
                sheets.extend(data)
        except Exception as e:
            print(f"Warning: Could not load {sheet_a_path}: {e}")
    
    # Load spfDataTemplate.json (secondary - reference sources)
    template_path = sheet_dir / "spfDataTemplate.json"
    if template_path.exists():
        try:
            with open(template_path, "r") as f:
                data = json.load(f)
                sheets.extend(data)
        except Exception as e:
            print(f"Warning: Could not load {template_path}: {e}")
    
    return sheets


def create_sheet_based_profile(sheet_entry: dict, variant_suffix: str = "") -> Optional[InstrumentProfile]:
    """
    Convert a sheet entry to InstrumentProfile.
    
    Args:
        sheet_entry: dict with az, el, dist, instrument, source_name, etc.
        variant_suffix: optional suffix for profile key (e.g., "_left", "_right")
    
    Returns:
        InstrumentProfile or None if mapping unclear
    """
    # Extract coordinates
    az = sheet_entry.get("az", sheet_entry.get("azimuth", 0.0))
    el = sheet_entry.get("el", sheet_entry.get("elevation", 0.0))
    dist = sheet_entry.get("dist", sheet_entry.get("distance", 0.7))
    
    instrument = sheet_entry.get("instrument", sheet_entry.get("instrument_category", "unknown"))
    role = sheet_entry.get("role", "unknown")
    
    source_name = sheet_entry.get("source_name", "Unknown")
    source_url = sheet_entry.get("source_url", "")
    pub_year = sheet_entry.get("publication_year", sheet_entry.get("year", 2026))
    attribution = sheet_entry.get("attribution", "")
    
    # Build citation
    citation = f"{source_name} ({pub_year}): {instrument} variant"
    if attribution:
        citation = f"{attribution} - {citation}"
    
    # Infer sensitivities from instrument type
    instrument_lower = instrument.lower()
    if "kick" in instrument_lower or "bass" in instrument_lower:
        energy_sens, flux_sens, bright_sens = 0.10, 0.08, 0.02
    elif "snare" in instrument_lower or "clap" in instrument_lower:
        energy_sens, flux_sens, bright_sens = 0.32, 0.35, 0.38
    elif "hat" in instrument_lower or "hi-hat" in instrument_lower:
        energy_sens, flux_sens, bright_sens = 0.28, 0.42, 0.45
    elif "tom" in instrument_lower or "floor" in instrument_lower:
        energy_sens, flux_sens, bright_sens = 0.30, 0.38, 0.32
    elif "cymbal" in instrument_lower or "crash" in instrument_lower:
        energy_sens, flux_sens, bright_sens = 0.35, 0.50, 0.50
    else:
        energy_sens, flux_sens, bright_sens = 0.15, 0.15, 0.20
    
    # Infer motion archetype
    if "kick" in instrument_lower or "bass" in instrument_lower:
        motion = "static"
    elif "hat" in instrument_lower or "snare" in instrument_lower or "tom" in instrument_lower:
        motion = "reactive"
    else:
        motion = "gentle_drift"
    
    return InstrumentProfile(
        category=instrument.lower().replace("-", "_"),
        role=role.lower().replace("-", "_"),
        base_azimuth_deg=float(az),
        azimuth_spread_deg=max(10.0, abs(float(az)) * 0.3),  # Heuristic spread
        base_elevation_deg=float(el),
        elevation_range_deg=max(5.0, abs(float(el)) * 0.4),  # Heuristic range
        base_distance=float(dist),
        default_spread=0.12 + (abs(float(az)) / 180.0) * 0.15,  # Wider for extreme azimuths
        motion_archetype=motion,
        energy_sensitivity=energy_sens,
        flux_sensitivity=flux_sens,
        brightness_sensitivity=bright_sens,
        source_citation=f"[DATA-SHEET] {citation}" + (f" {variant_suffix}" if variant_suffix else ""),
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
        Curated instrument profiles grounded in external reference sources.

        Convention:
        - azimuth 0 = dead centre (front).  Positive = right.
        - elevation 0 = ear level.  Positive = above.
        - distance 1.0 = far wall of cube.
        """

        # -- vocals (lead) -- front-centre (MusicGuyMixing 2023)
        self.instrument_profiles[("vocals", "lead")] = InstrumentProfile(
            category="vocals", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=15.0,
            base_elevation_deg=5.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.12,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.25,
            source_citation="MusicGuyMixing (2023): Lead Vocal dead center"
        )

        # -- vocals (backing / rhythm) -- +/- 60 deg (ProAudioFiles 2018)
        self.instrument_profiles[("vocals", "rhythm")] = InstrumentProfile(
            category="vocals", role="rhythm",
            base_azimuth_deg=60.0, azimuth_spread_deg=20.0,
            base_elevation_deg=8.0, elevation_range_deg=15.0,
            base_distance=0.70,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.20,
            source_citation="ProAudioFiles (2018): Backing vocals panned hard L/R at 60 deg"
        )
        
        # -- vocals (unknown) -- generic fallback
        self.instrument_profiles[("vocals", "unknown")] = self.instrument_profiles[("vocals", "rhythm")]

        # -- bass (bass) -- center, low (MusicGuyMixing 2023)
        self.instrument_profiles[("bass", "bass")] = InstrumentProfile(
            category="bass", role="bass",
            base_azimuth_deg=0.0, azimuth_spread_deg=10.0,
            base_elevation_deg=-5.0, elevation_range_deg=5.0,
            base_distance=0.55,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.08, flux_sensitivity=0.05, brightness_sensitivity=0.0,
            source_citation="MusicGuyMixing (2023): Electric/Double Bass center"
        )
        
        # -- bass (rhythm) -- essentially the same spatial profile as bass
        self.instrument_profiles[("bass", "rhythm")] = InstrumentProfile(
            category="bass", role="rhythm",
            base_azimuth_deg=0.0, azimuth_spread_deg=10.0,
            base_elevation_deg=-5.0, elevation_range_deg=5.0,
            base_distance=0.55,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.10, flux_sensitivity=0.05, brightness_sensitivity=0.0,
            source_citation="MusicGuyMixing (2023): Bass rhythms center"
        )

        # -- drums (percussion) / Overheads / Toms -- wide spread (DrumAudioEditing 2025 / ProAudioFiles 2018)
        self.instrument_profiles[("drums", "percussion")] = InstrumentProfile(
            category="drums", role="percussion",
            base_azimuth_deg=0.0, azimuth_spread_deg=65.0,
            base_elevation_deg=0.0, elevation_range_deg=20.0,
            base_distance=0.72,
            default_spread=0.22,
            motion_archetype="reactive",
            energy_sensitivity=0.35, flux_sensitivity=0.50, brightness_sensitivity=0.15,
            source_citation="DrumAudioEditing (2025): Overheads +/- 75deg, toms 60-90deg"
        )
        
        # -- percussion (rhythm) -- eg tambourine (MusicGuyMixing +/- 30 deg)
        self.instrument_profiles[("percussion", "rhythm")] = InstrumentProfile(
            category="percussion", role="rhythm",
            base_azimuth_deg=30.0, azimuth_spread_deg=15.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.70,
            default_spread=0.20,
            motion_archetype="reactive",
            energy_sensitivity=0.30, flux_sensitivity=0.45, brightness_sensitivity=0.20,
            source_citation="MusicGuyMixing (2023): Tambourine 30deg L/R"
        )
        
        # -- percussion (percussion)
        self.instrument_profiles[("percussion", "percussion")] = self.instrument_profiles[("percussion", "rhythm")]

        # -- guitar (rhythm) -- hard left/right (MusicGuyMixing: Acoustic/Electric +/- 90 deg)
        self.instrument_profiles[("guitar", "rhythm")] = InstrumentProfile(
            category="guitar", role="rhythm",
            base_azimuth_deg=90.0, azimuth_spread_deg=15.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.15,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.15, brightness_sensitivity=0.20,
            source_citation="MusicGuyMixing (2023): Electric Rhythm hard left/right"
        )

        # -- guitar (lead) -- center (MusicGuyMixing 2023)
        self.instrument_profiles[("guitar", "lead")] = InstrumentProfile(
            category="guitar", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=20.0,
            base_elevation_deg=3.0, elevation_range_deg=8.0,
            base_distance=0.60,
            default_spread=0.12,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.15, brightness_sensitivity=0.25,
            source_citation="MusicGuyMixing (2023): Electric Lead center"
        )

        # -- keys (rhythm) -- Piano Support (MusicGuyMixing 2023: +/- 30 to 90 deg)
        self.instrument_profiles[("keys", "rhythm")] = InstrumentProfile(
            category="keys", role="rhythm",
            base_azimuth_deg=45.0, azimuth_spread_deg=30.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.20,
            source_citation="MusicGuyMixing (2023): Piano support 30deg to hard panned"
        )
        
        # -- keys (lead) -- Synth Lead (MusicGuyMixing 2023: Center)
        self.instrument_profiles[("keys", "lead")] = InstrumentProfile(
            category="keys", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=15.0,
            base_elevation_deg=5.0, elevation_range_deg=15.0,
            base_distance=0.65,
            default_spread=0.15,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.15, brightness_sensitivity=0.30,
            source_citation="MusicGuyMixing (2023): Synth Lead center"
        )

        # -- strings (rhythm) -- wide, slightly elevated
        self.instrument_profiles[("strings", "rhythm")] = InstrumentProfile(
            category="strings", role="rhythm",
            base_azimuth_deg=0.0, azimuth_spread_deg=55.0,
            base_elevation_deg=10.0, elevation_range_deg=20.0,
            base_distance=0.75,
            default_spread=0.28,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.15, brightness_sensitivity=0.30,
            source_citation="SpatialSeed default (pre-2026)"
        )
        
        # -- strings (lead) -- slightly elevated & asymmetrical (Mock Data 2026: az -20, el 18)
        self.instrument_profiles[("strings", "lead")] = InstrumentProfile(
            category="strings", role="lead",
            base_azimuth_deg=-20.0, azimuth_spread_deg=30.0,
            base_elevation_deg=18.0, elevation_range_deg=25.0,
            base_distance=0.70,
            default_spread=0.25,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.25, flux_sensitivity=0.20, brightness_sensitivity=0.25,
            source_citation="Mock source (2026): Orchestral Strings Lead placement"
        )
        
        # -- horns (brass) -- Mock Data 2026: az 28, el 12
        self.instrument_profiles[("horns", "brass")] = InstrumentProfile(
            category="horns", role="brass",
            base_azimuth_deg=28.0, azimuth_spread_deg=25.0,
            base_elevation_deg=12.0, elevation_range_deg=15.0,
            base_distance=0.75,
            default_spread=0.22,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.30, flux_sensitivity=0.30, brightness_sensitivity=0.25,
            source_citation="Mock source (2026): Orchestral Horns/Brass placement"
        )
        
        # -- woodwinds (lead) -- Mock Data 2026: az -32, el 16
        self.instrument_profiles[("woodwinds", "lead")] = InstrumentProfile(
            category="woodwinds", role="lead",
            base_azimuth_deg=-32.0, azimuth_spread_deg=20.0,
            base_elevation_deg=16.0, elevation_range_deg=15.0,
            base_distance=0.70,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.20, brightness_sensitivity=0.25,
            source_citation="Mock source (2026): Chamber Woodwinds Lead placement"
        )
        
        # -- choir (ambience) -- Mock Data 2026: az 0, el 58
        self.instrument_profiles[("choir", "ambience")] = InstrumentProfile(
            category="choir", role="ambience",
            base_azimuth_deg=0.0, azimuth_spread_deg=80.0,
            base_elevation_deg=58.0, elevation_range_deg=20.0,
            base_distance=0.85,
            default_spread=0.35,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.15,
            source_citation="Mock source (2026): Choral Ambience height placement"
        )

        # -- pads (rhythm / ambience / fx) -- synth pads (MusicGuyMixing 2023: +/- 90 deg)
        self.instrument_profiles[("pads", "rhythm")] = InstrumentProfile(
            category="pads", role="rhythm",
            base_azimuth_deg=90.0, azimuth_spread_deg=50.0,
            base_elevation_deg=15.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.35,
            motion_archetype="orbit",
            energy_sensitivity=0.10, flux_sensitivity=0.05, brightness_sensitivity=0.15,
            source_citation="MusicGuyMixing (2023): Synth Pads hard L/R"
        )
        self.instrument_profiles[("pads", "fx")] = self.instrument_profiles[("pads", "rhythm")]

        # -- fx (fx) -- Reverb Ambience (InAIRSpace 2025: az 0, el 60)
        self.instrument_profiles[("fx", "fx")] = InstrumentProfile(
            category="fx", role="fx",
            base_azimuth_deg=0.0, azimuth_spread_deg=90.0,
            base_elevation_deg=60.0, elevation_range_deg=30.0,
            base_distance=0.85,
            default_spread=0.35,
            motion_archetype="reactive",
            energy_sensitivity=0.40, flux_sensitivity=0.60, brightness_sensitivity=0.30,
            source_citation="InAIRSpace (2025): Hall Reverb envelopment spatial mixing"
        )
        
        # -- sound_design (fx) -- Mock Data 2026: az 42, el 40
        self.instrument_profiles[("sound_design", "fx")] = InstrumentProfile(
            category="sound_design", role="fx",
            base_azimuth_deg=42.0, azimuth_spread_deg=60.0,
            base_elevation_deg=40.0, elevation_range_deg=30.0,
            base_distance=0.85,
            default_spread=0.30,
            motion_archetype="reactive",
            energy_sensitivity=0.45, flux_sensitivity=0.55, brightness_sensitivity=0.35,
            source_citation="Mock source (2026): Sound Design height placement"
        )

        # ======================================================================
        # AI-GENERATED PROFILES (v2 Coverage Expansion)
        # [AI-GENERATED] Source: Claude AI 2026-04-29 — created for extended
        # category/role coverage. Tuned to match spatial mixing conventions.
        # ======================================================================

        # -- percussion (melodic) -- mallets, vibraphone, pitched percussion
        self.instrument_profiles[("percussion", "melodic")] = InstrumentProfile(
            category="percussion", role="melodic",
            base_azimuth_deg=0.0, azimuth_spread_deg=25.0,
            base_elevation_deg=12.0, elevation_range_deg=18.0,
            base_distance=0.68,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.25, flux_sensitivity=0.30, brightness_sensitivity=0.35,
            source_citation="[AI-GENERATED] Vibraphone, marimba, pitched perc center-slightly elevated"
        )

        # -- percussion (mallet) -- timpani, xylophone, hard mallets
        self.instrument_profiles[("percussion", "mallet")] = InstrumentProfile(
            category="percussion", role="mallet",
            base_azimuth_deg=-15.0, azimuth_spread_deg=35.0,
            base_elevation_deg=20.0, elevation_range_deg=20.0,
            base_distance=0.72,
            default_spread=0.22,
            motion_archetype="reactive",
            energy_sensitivity=0.35, flux_sensitivity=0.40, brightness_sensitivity=0.40,
            source_citation="[AI-GENERATED] Timpani, xylophone elevated stereo spread"
        )

        # -- vocals (harmony) -- backing harmonies, gang vocals
        self.instrument_profiles[("vocals", "harmony")] = InstrumentProfile(
            category="vocals", role="harmony",
            base_azimuth_deg=0.0, azimuth_spread_deg=45.0,
            base_elevation_deg=8.0, elevation_range_deg=12.0,
            base_distance=0.72,
            default_spread=0.25,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.12, brightness_sensitivity=0.22,
            source_citation="[AI-GENERATED] Vocal harmony spread but cohesive, medium elevation"
        )

        # -- vocals (ambient) -- whispers, distant vocals, reverb trails
        self.instrument_profiles[("vocals", "ambient")] = InstrumentProfile(
            category="vocals", role="ambient",
            base_azimuth_deg=180.0, azimuth_spread_deg=80.0,
            base_elevation_deg=35.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.32,
            motion_archetype="orbit",
            energy_sensitivity=0.10, flux_sensitivity=0.08, brightness_sensitivity=0.15,
            source_citation="[AI-GENERATED] Ambient vocal envelopment rear/elevated"
        )

        # -- strings (pad) -- string pads, synth strings, orchestral swell
        self.instrument_profiles[("strings", "pad")] = InstrumentProfile(
            category="strings", role="pad",
            base_azimuth_deg=0.0, azimuth_spread_deg=60.0,
            base_elevation_deg=25.0, elevation_range_deg=25.0,
            base_distance=0.78,
            default_spread=0.30,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.20,
            source_citation="[AI-GENERATED] String pads enveloping, elevated-wide"
        )

        # -- brass (lead) -- trumpet, french horn leads
        self.instrument_profiles[("brass", "lead")] = InstrumentProfile(
            category="brass", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=18.0,
            base_elevation_deg=15.0, elevation_range_deg=12.0,
            base_distance=0.68,
            default_spread=0.14,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.28, flux_sensitivity=0.25, brightness_sensitivity=0.32,
            source_citation="[AI-GENERATED] Brass solo front-centered elevated"
        )

        # -- brass (harmony) -- brass harmonies, horn section backgrounds
        self.instrument_profiles[("brass", "harmony")] = InstrumentProfile(
            category="brass", role="harmony",
            base_azimuth_deg=45.0, azimuth_spread_deg=40.0,
            base_elevation_deg=18.0, elevation_range_deg=15.0,
            base_distance=0.72,
            default_spread=0.24,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.25, flux_sensitivity=0.22, brightness_sensitivity=0.28,
            source_citation="[AI-GENERATED] Brass section panned harmony"
        )

        # -- woodwinds (pad) -- clarinet pads, oboe pads, soft woodwinds
        self.instrument_profiles[("woodwinds", "pad")] = InstrumentProfile(
            category="woodwinds", role="pad",
            base_azimuth_deg=-45.0, azimuth_spread_deg=35.0,
            base_elevation_deg=12.0, elevation_range_deg=15.0,
            base_distance=0.70,
            default_spread=0.20,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.15, brightness_sensitivity=0.22,
            source_citation="[AI-GENERATED] Soft woodwind pads left-slightly elevated"
        )

        # -- woodwinds (harmony) -- saxophone section, clarinet choir
        self.instrument_profiles[("woodwinds", "harmony")] = InstrumentProfile(
            category="woodwinds", role="harmony",
            base_azimuth_deg=0.0, azimuth_spread_deg=50.0,
            base_elevation_deg=8.0, elevation_range_deg=12.0,
            base_distance=0.71,
            default_spread=0.26,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.22, flux_sensitivity=0.20, brightness_sensitivity=0.25,
            source_citation="[AI-GENERATED] Woodwind ensemble spread front-center"
        )

        # -- synth (lead) -- synth solo, monophonic synth line
        self.instrument_profiles[("synth", "lead")] = InstrumentProfile(
            category="synth", role="lead",
            base_azimuth_deg=0.0, azimuth_spread_deg=12.0,
            base_elevation_deg=5.0, elevation_range_deg=10.0,
            base_distance=0.65,
            default_spread=0.10,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.18, brightness_sensitivity=0.30,
            source_citation="[AI-GENERATED] Synth lead tight center slightly elevated"
        )

        # -- synth (pad) -- synth pads, atmospheric layers
        self.instrument_profiles[("synth", "pad")] = InstrumentProfile(
            category="synth", role="pad",
            base_azimuth_deg=0.0, azimuth_spread_deg=75.0,
            base_elevation_deg=22.0, elevation_range_deg=28.0,
            base_distance=0.82,
            default_spread=0.35,
            motion_archetype="orbit",
            energy_sensitivity=0.12, flux_sensitivity=0.08, brightness_sensitivity=0.18,
            source_citation="[AI-GENERATED] Synth pad enveloping ambient layer"
        )

        # -- synth (bass) -- synth bass, sub bass, electronic low end
        self.instrument_profiles[("synth", "bass")] = InstrumentProfile(
            category="synth", role="bass",
            base_azimuth_deg=0.0, azimuth_spread_deg=8.0,
            base_elevation_deg=-8.0, elevation_range_deg=6.0,
            base_distance=0.58,
            default_spread=0.12,
            motion_archetype="static",
            energy_sensitivity=0.08, flux_sensitivity=0.05, brightness_sensitivity=0.05,
            source_citation="[AI-GENERATED] Synth/electronic bass tight sub center"
        )

        # -- keys (pad) -- organ pad, electric piano swell
        self.instrument_profiles[("keys", "pad")] = InstrumentProfile(
            category="keys", role="pad",
            base_azimuth_deg=60.0, azimuth_spread_deg=40.0,
            base_elevation_deg=10.0, elevation_range_deg=15.0,
            base_distance=0.70,
            default_spread=0.22,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.14, flux_sensitivity=0.10, brightness_sensitivity=0.18,
            source_citation="[AI-GENERATED] Keys pad panned with gentle spread"
        )

        # -- guitar (fx) -- guitar effects, ambient guitar texture
        self.instrument_profiles[("guitar", "fx")] = InstrumentProfile(
            category="guitar", role="fx",
            base_azimuth_deg=-75.0, azimuth_spread_deg=50.0,
            base_elevation_deg=18.0, elevation_range_deg=20.0,
            base_distance=0.75,
            default_spread=0.28,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.20, brightness_sensitivity=0.25,
            source_citation="[AI-GENERATED] Guitar effects/ambience rear-elevated"
        )

        # -- guitar (bass) -- bass guitar, drop-tuned rhythm guitar
        self.instrument_profiles[("guitar", "bass")] = InstrumentProfile(
            category="guitar", role="bass",
            base_azimuth_deg=0.0, azimuth_spread_deg=12.0,
            base_elevation_deg=-6.0, elevation_range_deg=8.0,
            base_distance=0.60,
            default_spread=0.15,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.12, brightness_sensitivity=0.10,
            source_citation="[AI-GENERATED] Bass guitar low center slightly dynamic"
        )

        # -- drums (kick) -- kick drum, bass drum, sub kick
        self.instrument_profiles[("drums", "kick")] = InstrumentProfile(
            category="drums", role="kick",
            base_azimuth_deg=0.0, azimuth_spread_deg=6.0,
            base_elevation_deg=-10.0, elevation_range_deg=4.0,
            base_distance=0.52,
            default_spread=0.08,
            motion_archetype="static",
            energy_sensitivity=0.10, flux_sensitivity=0.08, brightness_sensitivity=0.02,
            source_citation="[AI-GENERATED] Kick drum sub-low center tight"
        )

        # -- drums (snare) -- snare, clap, rim shot
        self.instrument_profiles[("drums", "snare")] = InstrumentProfile(
            category="drums", role="snare",
            base_azimuth_deg=30.0, azimuth_spread_deg=20.0,
            base_elevation_deg=2.0, elevation_range_deg=8.0,
            base_distance=0.65,
            default_spread=0.12,
            motion_archetype="reactive",
            energy_sensitivity=0.32, flux_sensitivity=0.35, brightness_sensitivity=0.38,
            source_citation="[AI-GENERATED] Snare/clap right-center punchy"
        )

        # -- drums (hat) -- hi-hat, closed hat, open hat
        self.instrument_profiles[("drums", "hat")] = InstrumentProfile(
            category="drums", role="hat",
            base_azimuth_deg=-30.0, azimuth_spread_deg=15.0,
            base_elevation_deg=5.0, elevation_range_deg=10.0,
            base_distance=0.62,
            default_spread=0.10,
            motion_archetype="reactive",
            energy_sensitivity=0.28, flux_sensitivity=0.42, brightness_sensitivity=0.45,
            source_citation="[AI-GENERATED] Hi-hat left-center bright reactive"
        )

        # -- drums (tom) -- tom drums, floor tom, mid tom
        self.instrument_profiles[("drums", "tom")] = InstrumentProfile(
            category="drums", role="tom",
            base_azimuth_deg=-60.0, azimuth_spread_deg=25.0,
            base_elevation_deg=8.0, elevation_range_deg=12.0,
            base_distance=0.68,
            default_spread=0.16,
            motion_archetype="reactive",
            energy_sensitivity=0.30, flux_sensitivity=0.38, brightness_sensitivity=0.32,
            source_citation="[AI-GENERATED] Tom drum wide-left elevated reactive"
        )

        # -- bass (rhythm) -- already defined above; this is redundancy check
        # (kept to match original structure)

        # ======================================================================
        # STEREO DRUM VARIANTS from Data Sheets (v2.1)
        # Explicit left/right channel profiles for drum kit panning
        # ======================================================================

        # -- drums (hihat_left) -- Closed hi-hat left channel (MusicGuyMixing)
        self.instrument_profiles[("drums", "hihat_left")] = InstrumentProfile(
            category="drums", role="hihat_left",
            base_azimuth_deg=-30.0, azimuth_spread_deg=8.0,
            base_elevation_deg=0.0, elevation_range_deg=5.0,
            base_distance=0.62,
            default_spread=0.08,
            motion_archetype="reactive",
            energy_sensitivity=0.28, flux_sensitivity=0.42, brightness_sensitivity=0.45,
            source_citation="[DATA-SHEET] MusicGuyMixing (2023): Hi-Hat Left at -30°"
        )

        # -- drums (hihat_right) -- Closed hi-hat right channel (MusicGuyMixing)
        self.instrument_profiles[("drums", "hihat_right")] = InstrumentProfile(
            category="drums", role="hihat_right",
            base_azimuth_deg=30.0, azimuth_spread_deg=8.0,
            base_elevation_deg=0.0, elevation_range_deg=5.0,
            base_distance=0.62,
            default_spread=0.08,
            motion_archetype="reactive",
            energy_sensitivity=0.28, flux_sensitivity=0.42, brightness_sensitivity=0.45,
            source_citation="[DATA-SHEET] MusicGuyMixing (2023): Hi-Hat Right at +30°"
        )

        # -- drums (floortom_left) -- Floor tom left channel (DrumAudioEditing)
        self.instrument_profiles[("drums", "floortom_left")] = InstrumentProfile(
            category="drums", role="floortom_left",
            base_azimuth_deg=-90.0, azimuth_spread_deg=15.0,
            base_elevation_deg=0.0, elevation_range_deg=8.0,
            base_distance=0.68,
            default_spread=0.14,
            motion_archetype="reactive",
            energy_sensitivity=0.30, flux_sensitivity=0.38, brightness_sensitivity=0.32,
            source_citation="[DATA-SHEET] DrumAudioEditing (2025): Floor Tom Left at -90°"
        )

        # -- drums (floortom_right) -- Floor tom right channel (DrumAudioEditing)
        self.instrument_profiles[("drums", "floortom_right")] = InstrumentProfile(
            category="drums", role="floortom_right",
            base_azimuth_deg=90.0, azimuth_spread_deg=15.0,
            base_elevation_deg=0.0, elevation_range_deg=8.0,
            base_distance=0.68,
            default_spread=0.14,
            motion_archetype="reactive",
            energy_sensitivity=0.30, flux_sensitivity=0.38, brightness_sensitivity=0.32,
            source_citation="[DATA-SHEET] DrumAudioEditing (2025): Floor Tom Right at +90°"
        )

        # -- drums (rack_tom) -- Rack tom (mid tom center-right) (DrumAudioEditing)
        self.instrument_profiles[("drums", "rack_tom")] = InstrumentProfile(
            category="drums", role="rack_tom",
            base_azimuth_deg=45.0, azimuth_spread_deg=20.0,
            base_elevation_deg=10.0, elevation_range_deg=12.0,
            base_distance=0.68,
            default_spread=0.14,
            motion_archetype="reactive",
            energy_sensitivity=0.32, flux_sensitivity=0.38, brightness_sensitivity=0.35,
            source_citation="[DATA-SHEET] DrumAudioEditing (2025): Rack Tom Center-Right"
        )

        # -- drums (cymbal_crash) -- Crash cymbal (wide, bright)
        self.instrument_profiles[("drums", "cymbal_crash")] = InstrumentProfile(
            category="drums", role="cymbal_crash",
            base_azimuth_deg=0.0, azimuth_spread_deg=70.0,
            base_elevation_deg=15.0, elevation_range_deg=20.0,
            base_distance=0.72,
            default_spread=0.32,
            motion_archetype="reactive",
            energy_sensitivity=0.35, flux_sensitivity=0.50, brightness_sensitivity=0.50,
            source_citation="[DATA-SHEET] Studio standard: Crash cymbal wide bright"
        )

        # -- drums (cymbal_ride) -- Ride cymbal (center-right, sustained)
        self.instrument_profiles[("drums", "cymbal_ride")] = InstrumentProfile(
            category="drums", role="cymbal_ride",
            base_azimuth_deg=15.0, azimuth_spread_deg=25.0,
            base_elevation_deg=5.0, elevation_range_deg=8.0,
            base_distance=0.65,
            default_spread=0.16,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.25, flux_sensitivity=0.35, brightness_sensitivity=0.40,
            source_citation="[DATA-SHEET] Studio standard: Ride cymbal center-right"
        )

        # ======================================================================
        # ADDITIONAL SHEET-BASED VARIANTS (v2.1)
        # Derived from spfDataTemplate.json for genre/context variations
        # ======================================================================

        # -- vocals (choir_ambient) -- From template: choir at el 90
        self.instrument_profiles[("vocals", "choir_ambient")] = InstrumentProfile(
            category="vocals", role="choir_ambient",
            base_azimuth_deg=0.0, azimuth_spread_deg=85.0,
            base_elevation_deg=90.0, elevation_range_deg=15.0,
            base_distance=0.85,
            default_spread=0.38,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.15,
            source_citation="[DATA-SHEET] RalphSutton.com (2023): Choral envelopment overhead"
        )

        # -- strings (orchestral_ambience) -- From template: strings ambience elevated
        self.instrument_profiles[("strings", "orchestral_ambience")] = InstrumentProfile(
            category="strings", role="orchestral_ambience",
            base_azimuth_deg=0.0, azimuth_spread_deg=70.0,
            base_elevation_deg=60.0, elevation_range_deg=25.0,
            base_distance=0.82,
            default_spread=0.32,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.10, brightness_sensitivity=0.18,
            source_citation="[DATA-SHEET] RalphSutton.com (2023): Orchestral string ambient"
        )

        # ======================================================================
        # AMBIENT PADS & GRANULAR TEXTURES (v2.2 Content Focus)
        # [AI-GENERATED] 20 new profiles: ambient pads, granular, sound design,
        # field recordings. Tuned for envelopment, diffuseness, and spatial movement.
        # ======================================================================

        # -- ambient (pad_lush) -- Lush synth pad, enveloping, rear-elevated
        self.instrument_profiles[("ambient", "pad_lush")] = InstrumentProfile(
            category="ambient", role="pad_lush",
            base_azimuth_deg=180.0, azimuth_spread_deg=80.0,
            base_elevation_deg=40.0, elevation_range_deg=30.0,
            base_distance=0.85,
            default_spread=0.40,
            motion_archetype="orbit",
            energy_sensitivity=0.08, flux_sensitivity=0.05, brightness_sensitivity=0.12,
            source_citation="[AI-GENERATED] Lush ambient pad enveloping rear-elevated diffuse"
        )

        # -- ambient (pad_ethereal) -- Ethereal, sparse, high-freq content
        self.instrument_profiles[("ambient", "pad_ethereal")] = InstrumentProfile(
            category="ambient", role="pad_ethereal",
            base_azimuth_deg=90.0, azimuth_spread_deg=75.0,
            base_elevation_deg=70.0, elevation_range_deg=20.0,
            base_distance=0.88,
            default_spread=0.38,
            motion_archetype="orbit",
            energy_sensitivity=0.05, flux_sensitivity=0.03, brightness_sensitivity=0.20,
            source_citation="[AI-GENERATED] Ethereal ambient high-elevation sparse texture"
        )

        # -- ambient (pad_warm) -- Warm mid-range pad, front-centered
        self.instrument_profiles[("ambient", "pad_warm")] = InstrumentProfile(
            category="ambient", role="pad_warm",
            base_azimuth_deg=0.0, azimuth_spread_deg=40.0,
            base_elevation_deg=15.0, elevation_range_deg=20.0,
            base_distance=0.75,
            default_spread=0.28,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.10, flux_sensitivity=0.08, brightness_sensitivity=0.10,
            source_citation="[AI-GENERATED] Warm ambient pad front-centered diffuse"
        )

        # -- granular (texture_chaotic) -- Chaotic granular bursts, widely spread
        self.instrument_profiles[("granular", "texture_chaotic")] = InstrumentProfile(
            category="granular", role="texture_chaotic",
            base_azimuth_deg=0.0, azimuth_spread_deg=100.0,
            base_elevation_deg=0.0, elevation_range_deg=40.0,
            base_distance=0.78,
            default_spread=0.45,
            motion_archetype="reactive",
            energy_sensitivity=0.40, flux_sensitivity=0.55, brightness_sensitivity=0.45,
            source_citation="[AI-GENERATED] Chaotic granular texture burst, highly reactive diffuse"
        )

        # -- granular (texture_crystalline) -- Crystalline glitchy granules, elevated
        self.instrument_profiles[("granular", "texture_crystalline")] = InstrumentProfile(
            category="granular", role="texture_crystalline",
            base_azimuth_deg=30.0, azimuth_spread_deg=50.0,
            base_elevation_deg=50.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.35,
            motion_archetype="reactive",
            energy_sensitivity=0.32, flux_sensitivity=0.48, brightness_sensitivity=0.55,
            source_citation="[AI-GENERATED] Crystalline glitch granular elevated bright"
        )

        # -- granular (texture_organic) -- Organic pitched granular, drift motion
        self.instrument_profiles[("granular", "texture_organic")] = InstrumentProfile(
            category="granular", role="texture_organic",
            base_azimuth_deg=-45.0, azimuth_spread_deg=40.0,
            base_elevation_deg=20.0, elevation_range_deg=15.0,
            base_distance=0.72,
            default_spread=0.25,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.25, brightness_sensitivity=0.30,
            source_citation="[AI-GENERATED] Organic granular texture left-elevated drifting"
        )

        # -- sounddesign (whoosh) -- Whoosh/transition effect, fast pan motion
        self.instrument_profiles[("sounddesign", "whoosh")] = InstrumentProfile(
            category="sounddesign", role="whoosh",
            base_azimuth_deg=0.0, azimuth_spread_deg=80.0,
            base_elevation_deg=10.0, elevation_range_deg=25.0,
            base_distance=0.68,
            default_spread=0.30,
            motion_archetype="orbit",
            energy_sensitivity=0.50, flux_sensitivity=0.60, brightness_sensitivity=0.40,
            source_citation="[AI-GENERATED] Whoosh transition effect wide panned reactive"
        )

        # -- sounddesign (metallic_shine) -- Metallic/bell resonances, high-Q
        self.instrument_profiles[("sounddesign", "metallic_shine")] = InstrumentProfile(
            category="sounddesign", role="metallic_shine",
            base_azimuth_deg=45.0, azimuth_spread_deg=30.0,
            base_elevation_deg=35.0, elevation_range_deg=20.0,
            base_distance=0.65,
            default_spread=0.18,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.25, flux_sensitivity=0.35, brightness_sensitivity=0.60,
            source_citation="[AI-GENERATED] Metallic bell shine elevated bright reactive"
        )

        # -- sounddesign (underwater) -- Underwater/filtered ambience, rear
        self.instrument_profiles[("sounddesign", "underwater")] = InstrumentProfile(
            category="sounddesign", role="underwater",
            base_azimuth_deg=180.0, azimuth_spread_deg=60.0,
            base_elevation_deg=-20.0, elevation_range_deg=15.0,
            base_distance=0.80,
            default_spread=0.32,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.12, flux_sensitivity=0.08, brightness_sensitivity=0.05,
            source_citation="[AI-GENERATED] Underwater filtered reverb rear-low diffuse"
        )

        # -- sounddesign (digital_glitch) -- Digital glitch/artifact, scattered
        self.instrument_profiles[("sounddesign", "digital_glitch")] = InstrumentProfile(
            category="sounddesign", role="digital_glitch",
            base_azimuth_deg=-60.0, azimuth_spread_deg=70.0,
            base_elevation_deg=25.0, elevation_range_deg=30.0,
            base_distance=0.72,
            default_spread=0.35,
            motion_archetype="reactive",
            energy_sensitivity=0.45, flux_sensitivity=0.50, brightness_sensitivity=0.55,
            source_citation="[AI-GENERATED] Digital glitch artifact scattered high-elevation reactive"
        )

        # -- fieldrecording (wind_flutter) -- Field: wind/breath texture, diffuse
        self.instrument_profiles[("fieldrecording", "wind_flutter")] = InstrumentProfile(
            category="fieldrecording", role="wind_flutter",
            base_azimuth_deg=0.0, azimuth_spread_deg=85.0,
            base_elevation_deg=5.0, elevation_range_deg=30.0,
            base_distance=0.82,
            default_spread=0.40,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15, flux_sensitivity=0.20, brightness_sensitivity=0.08,
            source_citation="[AI-GENERATED] Field recording: wind/breath flutter diffuse"
        )

        # -- fieldrecording (rain_ambient) -- Field: rain texture, enveloping
        self.instrument_profiles[("fieldrecording", "rain_ambient")] = InstrumentProfile(
            category="fieldrecording", role="rain_ambient",
            base_azimuth_deg=180.0, azimuth_spread_deg=100.0,
            base_elevation_deg=45.0, elevation_range_deg=30.0,
            base_distance=0.86,
            default_spread=0.42,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.20, flux_sensitivity=0.25, brightness_sensitivity=0.15,
            source_citation="[AI-GENERATED] Field recording: rain ambient enveloping overhead"
        )

        # -- fieldrecording (water_flow) -- Field: water/stream, front-left
        self.instrument_profiles[("fieldrecording", "water_flow")] = InstrumentProfile(
            category="fieldrecording", role="water_flow",
            base_azimuth_deg=-30.0, azimuth_spread_deg=45.0,
            base_elevation_deg=-8.0, elevation_range_deg=12.0,
            base_distance=0.70,
            default_spread=0.28,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.22, brightness_sensitivity=0.10,
            source_citation="[AI-GENERATED] Field recording: water stream flow left-low"
        )

        # -- fieldrecording (forest_ambience) -- Field: forest/bird ambience, rear-elevated
        self.instrument_profiles[("fieldrecording", "forest_ambience")] = InstrumentProfile(
            category="fieldrecording", role="forest_ambience",
            base_azimuth_deg=120.0, azimuth_spread_deg=70.0,
            base_elevation_deg=35.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.35,
            motion_archetype="orbit",
            energy_sensitivity=0.15, flux_sensitivity=0.12, brightness_sensitivity=0.25,
            source_citation="[AI-GENERATED] Field recording: forest birds ambience rear-elevated"
        )

        # -- fieldrecording (urban_hum) -- Field: urban electrical hum/buzz
        self.instrument_profiles[("fieldrecording", "urban_hum")] = InstrumentProfile(
            category="fieldrecording", role="urban_hum",
            base_azimuth_deg=0.0, azimuth_spread_deg=30.0,
            base_elevation_deg=-15.0, elevation_range_deg=20.0,
            base_distance=0.68,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.08, flux_sensitivity=0.05, brightness_sensitivity=0.08,
            source_citation="[AI-GENERATED] Field recording: urban electrical hum low-center"
        )

        # -- ambient (decay_tail) -- Reverb decay tail, diffuse overhead
        self.instrument_profiles[("ambient", "decay_tail")] = InstrumentProfile(
            category="ambient", role="decay_tail",
            base_azimuth_deg=0.0, azimuth_spread_deg=90.0,
            base_elevation_deg=75.0, elevation_range_deg=15.0,
            base_distance=0.88,
            default_spread=0.35,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.05, flux_sensitivity=0.03, brightness_sensitivity=0.10,
            source_citation="[AI-GENERATED] Reverb decay tail diffuse overhead"
        )

        # -- ambient (resonance_ring) -- Resonant ring/swell, elevated orbit
        self.instrument_profiles[("ambient", "resonance_ring")] = InstrumentProfile(
            category="ambient", role="resonance_ring",
            base_azimuth_deg=90.0, azimuth_spread_deg=60.0,
            base_elevation_deg=50.0, elevation_range_deg=25.0,
            base_distance=0.80,
            default_spread=0.30,
            motion_archetype="orbit",
            energy_sensitivity=0.12, flux_sensitivity=0.08, brightness_sensitivity=0.18,
            source_citation="[AI-GENERATED] Resonant ring/swell elevated orbiting"
        )

        # -- granular (dust_particles) -- Granular 'dust' micro-particles, sparse
        self.instrument_profiles[("granular", "dust_particles")] = InstrumentProfile(
            category="granular", role="dust_particles",
            base_azimuth_deg=-90.0, azimuth_spread_deg=50.0,
            base_elevation_deg=60.0, elevation_range_deg=30.0,
            base_distance=0.75,
            default_spread=0.25,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.15, flux_sensitivity=0.20, brightness_sensitivity=0.35,
            source_citation="[AI-GENERATED] Granular dust particles left-rear-elevated sparse"
        )

        # -- sounddesign (morphing_texture) -- Morphing evolving texture, center orbit
        self.instrument_profiles[("sounddesign", "morphing_texture")] = InstrumentProfile(
            category="sounddesign", role="morphing_texture",
            base_azimuth_deg=0.0, azimuth_spread_deg=40.0,
            base_elevation_deg=25.0, elevation_range_deg=30.0,
            base_distance=0.76,
            default_spread=0.28,
            motion_archetype="orbit",
            energy_sensitivity=0.25, flux_sensitivity=0.30, brightness_sensitivity=0.35,
            source_citation="[AI-GENERATED] Morphing evolving texture center-elevated orbit"
        )

        # -- sounddesign (shimmer_halo) -- Shimmering halo effect, high-spread
        self.instrument_profiles[("sounddesign", "shimmer_halo")] = InstrumentProfile(
            category="sounddesign", role="shimmer_halo",
            base_azimuth_deg=45.0, azimuth_spread_deg=85.0,
            base_elevation_deg=55.0, elevation_range_deg=30.0,
            base_distance=0.82,
            default_spread=0.38,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.18, flux_sensitivity=0.15, brightness_sensitivity=0.50,
            source_citation="[AI-GENERATED] Shimmer halo effect high-spread elevated bright"
        )

        # -- ambient (void_infinite) -- Infinite void ambience, rear-far distance
        self.instrument_profiles[("ambient", "void_infinite")] = InstrumentProfile(
            category="ambient", role="void_infinite",
            base_azimuth_deg=180.0, azimuth_spread_deg=100.0,
            base_elevation_deg=0.0, elevation_range_deg=40.0,
            base_distance=0.92,
            default_spread=0.45,
            motion_archetype="orbit",
            energy_sensitivity=0.05, flux_sensitivity=0.02, brightness_sensitivity=0.05,
            source_citation="[AI-GENERATED] Infinite void ambience rear-far minimal energy"
        )

        # -- fieldrecording (traffic_distant) -- Field: distant traffic, front-low
        self.instrument_profiles[("fieldrecording", "traffic_distant")] = InstrumentProfile(
            category="fieldrecording", role="traffic_distant",
            base_azimuth_deg=0.0, azimuth_spread_deg=35.0,
            base_elevation_deg=-12.0, elevation_range_deg=18.0,
            base_distance=0.74,
            default_spread=0.24,
            motion_archetype="gentle_drift",
            energy_sensitivity=0.22, flux_sensitivity=0.20, brightness_sensitivity=0.15,
            source_citation="[AI-GENERATED] Field recording: distant traffic front-low drift"
        )

        # Load and integrate additional profiles from data sheets dynamically
        try:
            sheets = load_spf_data_sheets()
            for entry in sheets:
                # Skip entries we've already defined manually
                instrument_key = (entry.get("instrument", entry.get("instrument_category", "")).lower().replace("-", "_"),
                                entry.get("role", "unknown").lower().replace("-", "_"))
                
                if instrument_key not in self.instrument_profiles:
                    profile = create_sheet_based_profile(entry)
                    if profile:
                        self.instrument_profiles[instrument_key] = profile
        except Exception as e:
            # Non-fatal: data sheets are optional enhancements
            pass

        # -- fallback "other" / "unknown" -- mid-field, static
        self.instrument_profiles[("other", "unknown")] = InstrumentProfile(
            category="other", role="unknown",
            base_azimuth_deg=0.0, azimuth_spread_deg=40.0,
            base_elevation_deg=0.0, elevation_range_deg=10.0,
            base_distance=0.70,
            default_spread=0.20,
            motion_archetype="static",
            energy_sensitivity=0.10, flux_sensitivity=0.10, brightness_sensitivity=0.10,
            source_citation="SpatialSeed default fallback profile"
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
