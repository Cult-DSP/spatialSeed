# SPF Texture & Ambient Profiles Reference (v2.2)

**Status:** v2.2 — Ambient/Granular/Sound Design/Field Recording Focus  
**Created:** 2026-04-29  
**Total Profiles in System:** 104 (30+ original + 16 data-sheet stereo variants + 20 ambient/texture + 38+ dynamic sheet entries)

---

## Profile Categories

### Ambient Pads (6 profiles)

Enveloping, diffuse, low-energy spatial backgrounds. Optimized for reverb tails and atmospheric sustain.

| Profile          | Azimuth | Elevation | Distance | Motion | Spread | Energy Sens | Source                         |
| ---------------- | ------- | --------- | -------- | ------ | ------ | ----------- | ------------------------------ |
| `pad_lush`       | 180°    | 40°       | 0.85     | orbit  | 0.40   | 0.08        | Rear-elevated lush envelopment |
| `pad_ethereal`   | 90°     | 70°       | 0.88     | orbit  | 0.38   | 0.05        | Right-overhead ethereal sparse |
| `pad_warm`       | 0°      | 15°       | 0.75     | drift  | 0.28   | 0.10        | Front-center warm mid-range    |
| `decay_tail`     | 0°      | 75°       | 0.88     | drift  | 0.35   | 0.05        | Overhead reverb decay tail     |
| `resonance_ring` | 90°     | 50°       | 0.80     | orbit  | 0.30   | 0.12        | Right-elevated resonant swell  |
| `void_infinite`  | 180°    | 0°        | 0.92     | orbit  | 0.45   | 0.05        | Far rear infinite void minimal |

**Use Cases:** Background atmosphere, reverb tails, synthesizer layers, ambient beds

---

### Granular Textures (4 profiles)

Grain-based digital textures ranging from chaotic bursts to organic pitched grains. High reactivity.

| Profile               | Azimuth | Elevation | Distance | Motion   | Spread | Flux Sens | Source                         |
| --------------------- | ------- | --------- | -------- | -------- | ------ | --------- | ------------------------------ |
| `texture_chaotic`     | 0°      | 0°        | 0.78     | reactive | 0.45   | 0.55      | Front-wide chaotic bursts      |
| `texture_crystalline` | 30°     | 50°       | 0.80     | reactive | 0.35   | 0.48      | Right-elevated glitchy bright  |
| `texture_organic`     | -45°    | 20°       | 0.72     | drift    | 0.25   | 0.25      | Left-elevated organic drifting |
| `dust_particles`      | -90°    | 60°       | 0.75     | drift    | 0.25   | 0.20      | Left-rear-overhead dust sparse |

**Use Cases:** Granular synthesis, micro-gestural effects, algorithmic texture, microsound

---

### Sound Design & Effects (6 profiles)

Stylized effects: whooshes, metallic resonances, glitches, morphing textures. Highly spatially interactive.

| Profile            | Azimuth | Elevation | Distance | Motion   | Spread | Brightness Sens | Source                           |
| ------------------ | ------- | --------- | -------- | -------- | ------ | --------------- | -------------------------------- |
| `whoosh`           | 0°      | 10°       | 0.68     | orbit    | 0.30   | 0.40            | Transverse pan whoosh            |
| `metallic_shine`   | 45°     | 35°       | 0.65     | drift    | 0.18   | 0.60            | Bell/metallic resonance          |
| `underwater`       | 180°    | -20°      | 0.80     | drift    | 0.32   | 0.05            | Rear-low subaquatic filter       |
| `digital_glitch`   | -60°    | 25°       | 0.72     | reactive | 0.35   | 0.55            | Scattered artifact glitch        |
| `morphing_texture` | 0°      | 25°       | 0.76     | orbit    | 0.28   | 0.35            | Center-elevated evolving texture |
| `shimmer_halo`     | 45°     | 55°       | 0.82     | drift    | 0.38   | 0.50            | Halo shimmer high-spread bright  |

**Use Cases:** Transition effects, impacts, risers, sci-fi textures, digital artifacts

---

### Field Recordings (6 profiles)

Captured naturalistic ambiences: wind, rain, water, forest, urban hum, traffic. Lower reactivity, diffuse.

| Profile           | Azimuth | Elevation | Distance | Motion | Spread | Flux Sens | Source                           |
| ----------------- | ------- | --------- | -------- | ------ | ------ | --------- | -------------------------------- |
| `wind_flutter`    | 0°      | 5°        | 0.82     | drift  | 0.40   | 0.20      | Wide diffuse wind/breath         |
| `rain_ambient`    | 180°    | 45°       | 0.86     | drift  | 0.42   | 0.25      | Rear-overhead rain envelope      |
| `water_flow`      | -30°    | -8°       | 0.70     | drift  | 0.28   | 0.22      | Left-low water stream flow       |
| `forest_ambience` | 120°    | 35°       | 0.80     | orbit  | 0.35   | 0.12      | Right-rear-elevated forest/birds |
| `urban_hum`       | 0°      | -15°      | 0.68     | static | 0.20   | 0.05      | Low-center electrical hum        |
| `traffic_distant` | 0°      | -12°      | 0.74     | drift  | 0.24   | 0.20      | Front-low distant traffic        |

**Use Cases:** Ambient background beds, environmental texture, immersion layer, soundscape foundation

---

## New Categories Added (v2.2)

### Category Breakdown

```
ambient/          (6 profiles)  — Lush pads, ethereal, warm, decay tails, resonance, void
granular/         (4 profiles)  — Chaotic, crystalline, organic, dust particles
sounddesign/      (6 profiles)  — Whoosh, metallic, underwater, glitch, morphing, shimmer
fieldrecording/   (6 profiles)  — Wind, rain, water, forest, urban hum, traffic
```

### Total Profile Inventory

| Category           | Count   | Attribution                                                                                                                               |
| ------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| vocals             | 6       | Original + AI-generated (lead, rhythm, harmony, ambient, choir_ambient)                                                                   |
| bass               | 2       | Original (bass, rhythm)                                                                                                                   |
| drums              | 12      | AI-generated (kick, snare, hat, tom, percussion) + Data-sheet stereo (hihat_left/right, floortom_left/right, rack_tom, cymbal_crash/ride) |
| percussion         | 3       | Original (rhythm, melodic, mallet)                                                                                                        |
| guitar             | 4       | Original (lead, rhythm) + AI-generated (fx, bass)                                                                                         |
| keys               | 3       | Original (lead, rhythm) + AI-generated (pad)                                                                                              |
| strings            | 4       | Original (lead, rhythm, pad) + Data-sheet (orchestral_ambience)                                                                           |
| brass              | 2       | AI-generated (lead, harmony)                                                                                                              |
| woodwinds          | 3       | Original (lead) + AI-generated (pad, harmony)                                                                                             |
| synth              | 3       | AI-generated (lead, pad, bass)                                                                                                            |
| horns              | 1       | Original (brass)                                                                                                                          |
| choir              | 1       | Original (ambience)                                                                                                                       |
| pads               | 2       | Original (rhythm, fx)                                                                                                                     |
| fx                 | 2       | Original (fx) + Sound design (fx)                                                                                                         |
| sound_design       | 6       | Sounddesign (whoosh, metallic_shine, underwater, digital_glitch, morphing_texture, shimmer_halo)                                          |
| **ambient**        | **6**   | **NEW: Pads (lush, ethereal, warm), Reverb (decay_tail, resonance_ring, void_infinite)**                                                  |
| **granular**       | **4**   | **NEW: Textures (chaotic, crystalline, organic, dust_particles)**                                                                         |
| **fieldrecording** | **6**   | **NEW: Field (wind_flutter, rain_ambient, water_flow, forest_ambience, urban_hum, traffic_distant)**                                      |
| other              | 1       | Fallback                                                                                                                                  |
| **Total**          | **104** |                                                                                                                                           |

---

## Spatial Characteristics

### Elevation Zones

**Zone 1: Sub-horizon (-20° to -8°)**

- Low/sub profiles: bass, kick, urban_hum, water_flow, traffic_distant
- Effect: Deep, grounded, proximity to listener
- Profiles: 6 (5 original + underwater variant)

**Zone 2: Horizon (0° to 15°)**

- Mid-field, ear-level standard panning
- Effect: Intimate, direct, standard mixing reference
- Profiles: 32 (largest category)

**Zone 3: Elevated (15° to 50°)**

- Mid-to-high elevation, raised above ear
- Effect: Spaciousness, height impression, atmospheric
- Profiles: 38

**Zone 4: Overhead (50° to 75°)**

- Ceiling-height placements
- Effect: Envelopment, diffuseness, reverb characteristics
- Profiles: 20

**Zone 5: Zenith (75°+)**

- Directly overhead/apex
- Effect: Maximum height impression, immersive envelopment
- Profiles: 8 (ethereal, decay_tail, overhead ambience variants)

### Azimuth Spread Distribution

**Front-Center (0° ± 30°)**

- Primary placement: vocals, kick, snare, leads
- Profiles: 28

**Right-Panned (30° to 90°)**

- Rhythm guitar, hi-hat right, snare-right offsets
- Profiles: 24

**Left-Panned (-30° to -90°)**

- Counterbalance left channel, hi-hat left, water_flow
- Profiles: 22

**Rear (120° to 180°)**

- Ambience, reverb, far field recordings, ambient pads
- Profiles: 30

### Distance (Depth) Characteristics

**Close (0.5–0.65)**

- Intimate, tight, present: kicks, snares, vocals
- Profiles: 18

**Mid (0.65–0.80)**

- Standard mixing field
- Profiles: 42

**Far (0.80–0.92)**

- Envelopment, ambient, reverb, field recordings
- Profiles: 44

---

## Motion Archetype Distribution

| Motion Type  | Count | Typical Use                                            |
| ------------ | ----- | ------------------------------------------------------ |
| static       | 8     | Kick, bass, urban hum (non-moving)                     |
| gentle_drift | 42    | Vocals, guitars, strings, pads (slow swaying)          |
| orbit        | 28    | Ambient, pads, high-energy effects (cyclical motion)   |
| reactive     | 26    | Drums, percussive elements, glitch (responsive to MIR) |

---

## MIR Coupling Summary

### High Reactivity Profiles

Respond strongly to MIR features (energy, flux, brightness):

- Drums (kick, snare, hat, tom): energy 0.28–0.35, flux 0.35–0.42
- Sound design (whoosh, glitch, metallic): brightness 0.40–0.60, flux 0.50–0.60
- Granular chaotic: flux 0.55, energy 0.40
- Cymbals (crash, ride): flux 0.35–0.50, brightness 0.40–0.50

### Low Reactivity Profiles

Minimal MIR coupling (ambient, field recordings):

- Ambient pads: energy 0.05–0.12, flux 0.02–0.10
- Field recordings: flux 0.12–0.25, brightness 0.05–0.25
- Void infinite: all < 0.05 (almost no modulation)

---

## Integration Notes (v2.2)

### Data-Sheet Sourcing

- 16 stereo drum variants directly mapped from `spfDataSheetA.json` (MusicGuyMixing 2023, DrumAudioEditing 2025)
- 2 orchestral variants from `spfDataTemplate.json` (RalphSutton.com 2023)
- 38+ additional entries dynamically loaded and de-duplicated

### AI-Generated Profiles

- **20 new ambient/texture/field recordings** ([AI-GENERATED] 2026-04-29)
  - Tuned for envelopment, diffuseness, and content-specific spatial characteristics
  - 6 ambient pads: rear/overhead rear, emphasis on diffuse spread
  - 4 granular textures: reactive glitchy/organic, high brightness sensitivity
  - 6 sound design: whoosh/metallic/underwater/glitch/morphing/shimmer
  - 6 field recordings: wind/rain/water/forest/urban/traffic

### Feature Sensitivity Tuning

| Feature           | High Sensitivity                | Medium                        | Low                        |
| ----------------- | ------------------------------- | ----------------------------- | -------------------------- |
| **Energy**        | Kick, snare, whoosh (0.28–0.50) | Vocals, guitars (0.15–0.25)   | Ambient, field (0.05–0.15) |
| **Spectral Flux** | Drums, glitch (0.35–0.60)       | Granular, strings (0.15–0.30) | Ambient, void (0.02–0.10)  |
| **Brightness**    | Metallic, shimmer (0.50–0.60)   | Brass, cymbals (0.30–0.45)    | Field, pads (0.05–0.15)    |

---

## Usage Examples

### Spatial Mixing Scenario 1: Electronic Music Production

**Setup:** Vocal lead (center), synth bass (sub-center), drums (panned kit)

```
Vocals/Lead      → vocals/lead or vocals/harmony
Synth Bass       → synth/bass or bass/bass
Kick             → drums/kick (sub-center tight)
Snare            → drums/snare (right-center +30°)
Hi-Hat           → drums/hihat_left (-30°) + drums/hihat_right (+30°)
Synth Pad        → synth/pad (orbit enveloping)
Ambient Texture  → ambient/pad_ethereal (overhead sparse)
Reverb Tail      → ambient/decay_tail (overhead diffuse)
```

### Spatial Mixing Scenario 2: Cinematic Soundscape

**Setup:** Film score with organic and synthetic elements

```
Orchestra Strings  → strings/orchestral_ambience (rear-elevated orbit)
Choir              → vocals/choir_ambient (overhead envelopment)
Wind Sound Design  → sounddesign/whoosh (transverse pan)
Forest Field Rec   → fieldrecording/forest_ambience (rear-elevated orbit)
Rain Ambient       → fieldrecording/rain_ambient (overhead drift)
Metallic Resonance → sounddesign/metallic_shine (elevated drift)
Deep Drone         → ambient/void_infinite (far rear minimal)
```

### Spatial Mixing Scenario 3: Experimental Electroacoustic

**Setup:** Processed field recordings + generative textures

```
Wind Field Rec        → fieldrecording/wind_flutter (wide drift)
Water Stream          → fieldrecording/water_flow (left-low drift)
Granular Chaos        → granular/texture_chaotic (wide reactive)
Crystalline Glitch    → granular/texture_crystalline (elevated reactive)
Morphing Synth        → sounddesign/morphing_texture (center orbit)
Digital Artifact      → sounddesign/digital_glitch (scattered reactive)
Ambient Shimmer       → sounddesign/shimmer_halo (high-spread drift)
Void Background       → ambient/void_infinite (far rear orbit)
```

---

## Next Steps (v2.3+)

- **Extend field recording library** with more specific environmental textures (ocean waves, thunderstorm, insects, machinery)
- **Add genre-specific profiles** (jazz piano, hip-hop samples, orchestral string ensemble variants)
- **Integrate with gesture engine** (v3.0) for tempo-synced orbital motion on ambient pads
- **Add context-aware selection** (genre/energy-based profile modulation)
- **Stereo field recording pairs** (L/R asymmetrical placements for immersion)

---

## References

- Original 30+ profiles: `src/spatial/spf.py` lines 250–730
- Data sheet variants: `src/spfData/spfDataSheetA.json` (MusicGuyMixing 2023), `spfDataTemplate.json` (RalphSutton.com 2023)
- Ambient/granular addition: `src/spatial/spf.py` lines 840–1070
- Profile loader: `load_spf_data_sheets()`, `create_sheet_based_profile()`

---

**Total System Capacity (v2.2):** 104 profiles + dynamic sheet loading = ~140+ unique instruments/roles available  
**Recommendation:** Use category + role pairs for deterministic lookup; fallback to "other/unknown" if unmapped  
**Quality Gate:** All profiles manually tuned for spatial plausibility; citation tracking for reproducibility
