"""
SpatialSeed Streamlit UI
=========================
Local web UI for SpatialSeed spatial authoring.

Per spec: DesignSpecV1.md section 6, agents.md section 13

Features:
- Seed Matrix 2D control (u, v) with interactive canvas
- Stem discovery + category/role override controls
- Generate button with per-stage progress
- Results: keyframe statistics, spatial placement summary, export paths
- Diagnostics: per-object keyframe counts, classification confidence
"""

import json
import os
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------------------------------------------------------
# Ensure src/ is importable regardless of how streamlit launches
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline import SpatialSeedPipeline
from src.core.session import SessionManager
from src.mir.classify import InstrumentClassifier


# ======================================================================
# Constants
# ======================================================================

CATEGORIES = InstrumentClassifier.CATEGORIES  # canonical category list
ROLES = InstrumentClassifier.ROLES  # canonical role list


# ======================================================================
# Session-state helpers
# ======================================================================

def _init_state():
    """Initialise Streamlit session-state keys if absent."""
    defaults = {
        "manifest": None,
        "classifications": None,
        "overrides": {},  # node_id -> {"category": ..., "role_hint": ...}
        "results": None,
        "run_log": "",
        "pipeline_running": False,
        "stems_discovered": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ======================================================================
# Stem discovery (lightweight -- Stage 0 only)
# ======================================================================

def _discover_stems(project_dir: str, stems_dir: str):
    """Run Stage 0 only to populate session state with stem list."""
    session = SessionManager(project_dir, stems_dir)
    manifest = session.run()
    st.session_state["manifest"] = manifest
    st.session_state["stems_discovered"] = True
    # Reset stale data
    st.session_state["classifications"] = None
    st.session_state["overrides"] = {}
    st.session_state["results"] = None


# ======================================================================
# Pipeline execution with override injection
# ======================================================================

def _run_pipeline(
    project_dir: str,
    stems_dir: str,
    u: float,
    v: float,
    overrides: Dict,
):
    """Run the full pipeline, capturing stdout as a log."""
    pipeline = SpatialSeedPipeline(
        project_dir=project_dir,
        stems_dir=stems_dir,
    )
    results = pipeline.run(
        u=u,
        v=v,
        export_adm=False,
        classification_overrides=overrides if overrides else None,
    )
    return results


# ======================================================================
# UI Components
# ======================================================================

def _render_sidebar():
    """Render sidebar controls. Returns (project_dir, stems_dir, u, v)."""
    with st.sidebar:
        # Project Settings Panel
        st.markdown('<div class="section-header">Project Settings</div>', unsafe_allow_html=True)

        base_dir = st.text_input(
            "Base Output Directory",
            value=str(_REPO_ROOT / "test_session"),
            help="Root directory for sessions",
            label_visibility="collapsed"
        )
        st.caption("Base Output Directory")

        session_name = st.text_input(
            "Session Name",
            value="my_session",
            help="Name of this specific session",
            label_visibility="collapsed"
        )
        st.caption("Session Name")
        
        project_dir = str(Path(base_dir) / session_name)

        stems_dir = st.text_input(
            "Stems Directory",
            value=str(_REPO_ROOT / "test_session" / "stems"),
            help="Folder containing input stereo WAV stems",
            label_visibility="collapsed"
        )
        st.caption("Stems Directory")

        st.markdown("---")

        # Seed Matrix Panel
        st.markdown('<div class="section-header">Seed Matrix</div>', unsafe_allow_html=True)
        st.caption("Control aesthetic and motion characteristics")

        u = st.slider(
            "u — Aesthetic Variation",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.01,
            help="0 = conservative / centred, 1 = experimental / wide",
            label_visibility="collapsed"
        )
        st.caption("u — Aesthetic Variation")

        v = st.slider(
            "v — Dynamic Immersion",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.01,
            help="0 = mostly static, 1 = enveloping / animated",
            label_visibility="collapsed"
        )
        st.caption("v — Dynamic Immersion")

        # Current values display
        st.markdown(f'<div class="technical-text">(u={u:.2f}, v={v:.2f})</div>', unsafe_allow_html=True)

        # 2D Canvas Visualization with enhanced styling
        st.markdown("---")
        st.markdown('<div class="section-header">Matrix View</div>', unsafe_allow_html=True)

        # Create the seed matrix container
        st.markdown('<div class="seed-matrix-container">', unsafe_allow_html=True)

        df = pd.DataFrame({"u": [u], "v": [v], "label": ["Current Selection"]})
        chart = alt.Chart(df).mark_circle(
            size=300,
            color="#4a90e2",
            opacity=0.8
        ).encode(
            x=alt.X("u:Q", scale=alt.Scale(domain=[0, 1]), title="u — Aesthetic Variation"),
            y=alt.Y("v:Q", scale=alt.Scale(domain=[0, 1]), title="v — Dynamic Immersion"),
            tooltip=["u", "v"]
        ).properties(
            height=280,
            background='transparent',
            padding={'left': 60, 'right': 20, 'top': 40, 'bottom': 60}
        ).configure_axis(
            grid=True,
            gridDash=[2,2],
            gridColor='#e8e6e3',
            domainColor='#d4d2cf',
            tickColor='#d4d2cf',
            labelColor='#ffffff',  # White for axis numbers
            titleColor='#ffffff',  # White for axis titles
            titleFontSize=12,
            labelFontSize=11,
            titleFont='SF Pro Display, Inter, sans-serif',
            labelFont='SF Pro Display, Inter, sans-serif',
            titlePadding=20,
            labelPadding=8
        ).configure_view(
            strokeWidth=0
        )
        st.altair_chart(chart, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.caption("SpatialSeed v0.1.0")

    return project_dir, stems_dir, u, v


def _render_generate_tab(project_dir: str, stems_dir: str, u: float, v: float):
    """Render the Generate tab."""
    st.markdown('<div class="section-header">Generate Spatial Scene</div>', unsafe_allow_html=True)

    # Control cards in a row
    col_disc, col_gen = st.columns([1, 1])

    with col_disc:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Discover Stems**")
        st.caption("Scan the stems directory and analyze audio files")
        if st.button("Discover Stems", width='stretch'):
            with st.spinner("Discovering stems..."):
                try:
                    _discover_stems(project_dir, stems_dir)
                    st.success(
                        f"Found {st.session_state['manifest']['stem_count']} stems "
                        f"({st.session_state['manifest']['object_count']} objects)"
                    )
                except Exception as exc:
                    st.error(f"Discovery failed: {exc}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_gen:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Generate Scene**")
        st.caption("Create spatial scene using current seed matrix settings")
        generate_disabled = not st.session_state.get("stems_discovered", False)
        if st.button(
            "Generate Scene",
            type="primary",
            width='stretch',
            disabled=generate_disabled,
        ):
            overrides = st.session_state.get("overrides", {})
            progress_bar = st.progress(0, text="Initialising...")
            log_area = st.empty()
            t0 = time.time()

            stage_names = [
                "Session + Discovery",
                "Normalize + Split Audio",
                "MIR Extraction",
                "Classification",
                "Seed Matrix",
                "SPF Resolution",
                "Static Placement",
                "Gesture Generation",
                "LUSID Scene Assembly",
                "LUSID Package Export",
            ]
            try:
                # Capture stdout
                old_stdout = sys.stdout
                capture = StringIO()
                sys.stdout = capture

                results = _run_pipeline(
                    project_dir, stems_dir, u, v, overrides
                )

                sys.stdout = old_stdout
                captured_log = capture.getvalue()

                progress_bar.progress(100, text="Complete")
                elapsed = time.time() - t0
                st.success(f"Pipeline complete in {elapsed:.1f}s")

                st.session_state["results"] = results
                st.session_state["run_log"] = captured_log

            except Exception as exc:
                sys.stdout = old_stdout
                st.error(f"Pipeline failed: {exc}")
                st.exception(exc)
        st.markdown('</div>', unsafe_allow_html=True)

    if generate_disabled:
        st.info("Click **Discover Stems** first to scan the stems directory.")

    # Pipeline reference in a card
    st.markdown("---")
    with st.expander("Pipeline Stages Reference", expanded=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        pipeline_stages = [
            "Session + Discovery",
            "Normalize + Split Audio (48 kHz, stereo split, bed generation)",
            "MIR Feature Extraction (librosa)",
            "Classification + Role Assignment",
            "Seed Matrix Selection (u,v) → style vector z",
            "SPF Resolution → StyleProfile per object",
            "Static Placement (Cartesian cube)",
            "Gesture Generation (sparse keyframes)",
            "LUSID Scene Assembly (scene.lusid.json)",
            "LUSID Package Export (containsAudio.json, WAV copy)",
        ]
        for i, name in enumerate(pipeline_stages):
            st.markdown(f"**{i}:** {name}")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_stems_tab():
    """Render the Stems tab with classification overrides."""
    st.markdown('<div class="section-header">Stems + Classification Overrides</div>', unsafe_allow_html=True)

    manifest = st.session_state.get("manifest")
    if manifest is None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("No stems discovered yet. Go to the **Generate** tab and click **Discover Stems**.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    stems = manifest["stems"]

    # Summary card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write(
        f"**{len(stems)} stems** discovered "
        f"({manifest['object_count']} objects, "
        f"max duration {manifest['max_duration_seconds']:.1f}s)"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    overrides = st.session_state.get("overrides", {})
    results = st.session_state.get("results")

    # Build a row per stem with card styling
    for i, stem in enumerate(stems):
        with st.expander(f"Stem {i+1}: {stem['filename']}", expanded=(i < 3)):
            st.markdown('<div class="card">', unsafe_allow_html=True)

            # Stem metadata
            meta_cols = st.columns(4)
            meta_cols[0].metric("Sample Rate", f"{stem['sample_rate']} Hz")
            meta_cols[1].metric("Channels", stem["channels"])
            meta_cols[2].metric("Duration", f"{stem['duration_seconds']:.1f}s")
            meta_cols[3].metric(
                "Objects",
                len(stem["group_ids"]),
            )

            st.caption(f"Node IDs: {', '.join(stem['node_ids'])}  |  Hash: {stem['hash'][:16]}...")

            # Classification info (if pipeline has run)
            if results and "classifications" in results:
                cls_data = results["classifications"]
                for nid in stem["node_ids"]:
                    cls = cls_data.get(nid, {})
                    if cls:
                        st.write(
                            f"**{nid}:** category=`{cls.get('category', '?')}` "
                            f"role=`{cls.get('role_hint', '?')}` "
                            f"(fallbacks: {cls.get('fallbacks_used', [])})"
                        )

            # Override controls -- one row per node
            st.markdown("**Override classification** (leave as 'auto' to use pipeline result):")
            for nid in stem["node_ids"]:
                c1, c2 = st.columns(2)
                current_cat = overrides.get(nid, {}).get("category", "auto")
                current_role = overrides.get(nid, {}).get("role_hint", "auto")

                cat_options = ["auto"] + CATEGORIES
                role_options = ["auto"] + ROLES

                new_cat = c1.selectbox(
                    f"Category ({nid})",
                    options=cat_options,
                    index=cat_options.index(current_cat) if current_cat in cat_options else 0,
                    key=f"cat_{nid}",
                    label_visibility="collapsed"
                )
                c1.caption(f"Category ({nid})")

                new_role = c2.selectbox(
                    f"Role ({nid})",
                    options=role_options,
                    index=role_options.index(current_role) if current_role in role_options else 0,
                    key=f"role_{nid}",
                    label_visibility="collapsed"
                )
                c2.caption(f"Role ({nid})")

                # Update overrides in session state
                if new_cat != "auto" or new_role != "auto":
                    ov = {}
                    if new_cat != "auto":
                        ov["category"] = new_cat
                    if new_role != "auto":
                        ov["role_hint"] = new_role
                    overrides[nid] = ov
                elif nid in overrides:
                    del overrides[nid]

            st.markdown('</div>', unsafe_allow_html=True)

    st.session_state["overrides"] = overrides

    if overrides:
        st.markdown("---")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**Active overrides:**")
        for nid, ov in sorted(overrides.items()):
            parts = []
            if "category" in ov:
                parts.append(f"category={ov['category']}")
            if "role_hint" in ov:
                parts.append(f"role={ov['role_hint']}")
            st.write(f"- `{nid}`: {', '.join(parts)}")
        st.caption("Overrides are applied on the next Generate run.")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_results_tab():
    """Render the Results tab."""
    st.markdown('<div class="section-header">Results</div>', unsafe_allow_html=True)

    results = st.session_state.get("results")
    if results is None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("No results yet. Run the pipeline from the **Generate** tab.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # -- Summary metrics in a card -----------------------------------------------
    st.markdown('<div class="section-header">Summary</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    kf_stats = results.get("keyframe_stats", {})
    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Total Objects", kf_stats.get("total_objects", "?"))
    m2.metric("Total Keyframes", kf_stats.get("total_keyframes", "?"))
    m3.metric("Static Objects", kf_stats.get("static_objects", "?"))
    m4.metric("Animated Objects", kf_stats.get("animated_objects", "?"))

    st.write(
        f"Avg keyframes/object: **{kf_stats.get('avg_keyframes_per_object', '?')}**"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # -- Style vector in a card --------------------------------------------------
    st.markdown('<div class="section-header">Style Vector</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    z = results.get("style_vector", [])
    if z:
        dim_names = [
            "spread_width", "height_usage", "front_back_bias",
            "motion_intensity", "motion_complexity", "motion_periodicity",
            "onset_reactivity", "spectral_brightness",
        ]
        cols = st.columns(len(z))
        for idx, (name, val) in enumerate(zip(dim_names, z)):
            cols[idx].metric(name, f"{val:.2f}")
    st.markdown('</div>', unsafe_allow_html=True)

    # -- Export paths in a card --------------------------------------------------
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    lusid_pkg = results.get("lusid_package", "")
    if lusid_pkg:
        st.write(f"LUSID package: `{lusid_pkg}`")

        pkg_path = Path(lusid_pkg)
        if pkg_path.is_dir():
            files = sorted(pkg_path.iterdir())
            wav_count = sum(1 for f in files if f.suffix == ".wav")
            json_count = sum(1 for f in files if f.suffix == ".json")
            st.write(f"  {json_count} JSON files, {wav_count} WAV files")
    st.markdown('</div>', unsafe_allow_html=True)

    # -- Scene details in a card -------------------------------------------------
    scene_info = results.get("scene_info")
    if scene_info:
        st.markdown('<div class="section-header">LUSID Scene</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Frames", scene_info.get("frame_count", "?"))
        sc2.metric("Audio Object Entries", scene_info.get("audio_object_entries", "?"))
        sc3.metric("Bed/LFE Entries", scene_info.get("bed_entries", "?"))
        st.markdown('</div>', unsafe_allow_html=True)

    # -- Per-object classification table in a card --------------------------------
    cls_data = results.get("classifications")
    if cls_data:
        st.markdown('<div class="section-header">Classifications</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        rows = []
        for nid in sorted(cls_data.keys(), key=lambda x: [int(p) for p in x.split(".")]):
            c = cls_data[nid]
            rows.append({
                "Node": nid,
                "Category": c.get("category", "?"),
                "Role": c.get("role_hint", "?"),
                "Confidence": f"{c.get('category_confidence', 0):.2f}",
                "Fallbacks": ", ".join(c.get("fallbacks_used", [])),
            })
        st.table(rows)
        st.markdown('</div>', unsafe_allow_html=True)

    # -- Run log in an expander -------------------------------------------------------
    run_log = st.session_state.get("run_log", "")
    if run_log:
        with st.expander("Pipeline Log", expanded=False):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.code(run_log, language="text")
            st.markdown('</div>', unsafe_allow_html=True)


# ======================================================================
# Main
# ======================================================================

def main():
    """Streamlit UI entry point."""
    st.set_page_config(
        page_title="SpatialSeed",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for SpatialSeed design system
    st.markdown("""
    <style>
    /* Design System Variables */
    :root {
        --bg-primary: #faf9f7;
        --bg-secondary: #ffffff;
        --bg-tertiary: #f8f7f5;
        --text-primary: #2c2c2c;
        --text-secondary: #666666;
        --text-muted: #999999;
        --border-light: #e8e6e3;
        --border-medium: #d4d2cf;
        --accent-blue: #4a90e2;
        --accent-blue-light: #e8f2ff;
        --shadow-light: 0 1px 3px rgba(0,0,0,0.1);
        --shadow-medium: 0 2px 8px rgba(0,0,0,0.12);
        --shadow-heavy: 0 4px 16px rgba(0,0,0,0.15);
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --spacing-xs: 4px;
        --spacing-sm: 8px;
        --spacing-md: 16px;
        --spacing-lg: 24px;
        --spacing-xl: 32px;
        --font-mono: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        --font-sans: 'SF Pro Display', 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Global overrides */
    .main {
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }

    .stApp {
        background-color: var(--bg-primary) !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em !important;
    }

    .stTitle {
        font-size: 2rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        margin-bottom: var(--spacing-sm) !important;
    }

    .stCaption {
        color: var(--text-secondary) !important;
        font-size: 0.875rem !important;
        font-family: var(--font-sans) !important;
    }

    /* Section headers - uppercase letterspaced */
    .section-header {
        font-family: var(--font-sans) !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: var(--text-secondary) !important;
        margin-bottom: var(--spacing-md) !important;
        border-bottom: 1px solid var(--border-light) !important;
        padding-bottom: var(--spacing-xs) !important;
    }

    /* Technical text - monospace */
    .technical-text, .stCode, code {
        font-family: var(--font-mono) !important;
        font-size: 0.8rem !important;
        color: var(--text-secondary) !important;
        background-color: var(--bg-tertiary) !important;
        padding: var(--spacing-xs) var(--spacing-sm) !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border-light) !important;
    }

    /* Cards and panels */
    .card {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        padding: var(--spacing-lg) !important;
        box-shadow: var(--shadow-light) !important;
        margin-bottom: var(--spacing-md) !important;
    }

    .card:hover {
        box-shadow: var(--shadow-medium) !important;
        transition: box-shadow 0.2s ease !important;
    }

    /* Status pill */
    .status-pill {
        display: inline-block !important;
        padding: var(--spacing-xs) var(--spacing-sm) !important;
        border-radius: 12px !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        background-color: var(--bg-tertiary) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border-light) !important;
    }

    .status-pill.ready {
        background-color: #e8f5e8 !important;
        color: #2e7d32 !important;
        border-color: #4caf50 !important;
    }

    .status-pill.generating {
        background-color: var(--accent-blue-light) !important;
        color: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
    }

    /* Sidebar styling */
    .css-1d391kg, .css-12oz5g7 {  /* sidebar container */
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-light) !important;
    }

    .sidebar .stTextInput, .sidebar .stSelectbox, .sidebar .stSlider {
        background-color: var(--bg-tertiary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-sm) !important;
        padding: var(--spacing-sm) !important;
    }

    /* Buttons */
    .stButton button {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-md) !important;
        padding: var(--spacing-sm) var(--spacing-lg) !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    .stButton button:hover {
        background-color: var(--bg-tertiary) !important;
        box-shadow: var(--shadow-light) !important;
        transform: translateY(-1px) !important;
    }

    .stButton button:active {
        transform: translateY(0) !important;
    }

    .stButton button[data-testid="stBaseButton-primary"] {
        background-color: var(--accent-blue) !important;
        color: white !important;
        border-color: var(--accent-blue) !important;
    }

    .stButton button[data-testid="stBaseButton-primary"]:hover {
        background-color: #3a7bd5 !important;
        box-shadow: var(--shadow-medium) !important;
    }

    /* Sliders */
    .stSlider .st-bs {
        background-color: var(--accent-blue) !important;
    }

    .stSlider .st-cq {
        background-color: var(--border-light) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 1px solid var(--border-light) !important;
        gap: var(--spacing-lg) !important;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
        padding: var(--spacing-sm) var(--spacing-md) !important;
        border: none !important;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-light) !important;
        border-bottom: 1px solid var(--bg-secondary) !important;
        box-shadow: var(--shadow-light) !important;
    }

    /* Metrics */
    .stMetric {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        padding: var(--spacing-md) !important;
        box-shadow: var(--shadow-light) !important;
    }

    .stMetric label {
        color: var(--text-secondary) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    .stMetric .metric-value {
        color: var(--text-primary) !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }

    /* Altair chart styling */
    .stAltairChart {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        padding: var(--spacing-md) !important;
        box-shadow: var(--shadow-light) !important;
        overflow: visible !important;
    }

    /* Ensure Altair text is visible */
    .stAltairChart text {
        fill: var(--text-primary) !important;
        font-family: var(--font-sans) !important;
    }

    .stAltairChart .role-axis-title text {
        fill: var(--text-primary) !important;
        font-weight: 500 !important;
    }

    /* Progress bars */
    .stProgress .st-bo {
        background-color: var(--accent-blue) !important;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: var(--bg-tertiary) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        font-family: var(--font-sans) !important;
        font-weight: 500 !important;
    }

    /* Tables */
    .stTable {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-light) !important;
    }

    .stTable th {
        background-color: var(--bg-tertiary) !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-size: 0.75rem !important;
        padding: var(--spacing-sm) var(--spacing-md) !important;
    }

    .stTable td {
        padding: var(--spacing-sm) var(--spacing-md) !important;
        border-bottom: 1px solid var(--border-light) !important;
    }

    /* Seed Matrix specific styling */
    .seed-matrix-container {
        background: linear-gradient(45deg, transparent 49%, var(--border-light) 49%, var(--border-light) 51%, transparent 51%),
                    linear-gradient(-45deg, transparent 49%, var(--border-light) 49%, var(--border-light) 51%, transparent 51%);
        background-size: 20px 20px;
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-light);
        border-radius: var(--radius-lg);
        padding: var(--spacing-xl);
        box-shadow: var(--shadow-medium);
        position: relative;
        overflow: visible;
    }

    /* Hide default Streamlit elements */
    #MainMenu, footer, .css-1rs6os { display: none !important; }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-tertiary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border-medium);
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    </style>
    """, unsafe_allow_html=True)

    _init_state()

    # App header with status
    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.title("SpatialSeed")
        st.caption("Immersive Spatial Scene Authoring — LUSID-first pipeline")
    with col_status:
        status = "READY" if not st.session_state.get("pipeline_running", False) else "GENERATING"
        status_class = "ready" if status == "READY" else "generating"
        st.markdown(f'<div class="status-pill {status_class}">{status}</div>', unsafe_allow_html=True)

    project_dir, stems_dir, u, v = _render_sidebar()

    # Main tabs with updated styling
    tab_gen, tab_stems, tab_results = st.tabs(["Generate", "Stems", "Results"])

    with tab_gen:
        _render_generate_tab(project_dir, stems_dir, u, v)

    with tab_stems:
        _render_stems_tab()

    with tab_results:
        _render_results_tab()


if __name__ == "__main__":
    main()
("SpatialSeed")
        st.caption("Immersive Spatial Scene Authoring — LUSID-first pipeline")
    with col_status:
        status = "READY" if not st.session_state.get("pipeline_running", False) else "GENERATING"
        status_class = "ready" if status == "READY" else "generating"
        st.markdown(f'<div class="status-pill {status_class}">{status}</div>', unsafe_allow_html=True)

    project_dir, stems_dir, u, v = _render_sidebar()

    # Main tabs with updated styling
    tab_gen, tab_stems, tab_results = st.tabs(["Generate", "Stems", "Results"])

    with tab_gen:
        _render_generate_tab(project_dir, stems_dir, u, v)

    with tab_stems:
        _render_stems_tab()

    with tab_results:
        _render_results_tab()


if __name__ == "__main__":
    main()
s_tab()


if __name__ == "__main__":
    main()
