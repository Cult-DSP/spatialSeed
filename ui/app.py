"""
SpatialSeed Streamlit UI — Spatial Root Aesthetic Alignment
============================================================
Local web UI for SpatialSeed spatial authoring, styled to align with Spatial Root UI.

Features:
- Dark application background with warm parchment control panels.
- Monospaced technical typography.
- Compact tabbed workflow: AUTHOR, ANALYZE, EXPORT, RESULTS, LOGS.
- Status indicator in the header: IDLE, READY, RUNNING, ERROR, EXPORTED.
- Utilitarian, professional audio-tool layout.
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

# Colors based on Spatial Root aesthetic
COLOR_DARK_BG = "#0f0f0f"
COLOR_PARCHMENT = "#f5f2e9"
COLOR_PARCHMENT_LIGHT = "#faf9f5"
COLOR_BORDER = "#d1cdc2"
COLOR_TEXT_DARK = "#1a1a1a"
COLOR_TEXT_LIGHT = "#e0e0e0"
COLOR_ACCENT = "#8c887d"
COLOR_STATUS_IDLE = "#666666"
COLOR_STATUS_READY = "#8c887d"
COLOR_STATUS_RUNNING = "#c9a66b" # warm gold
COLOR_STATUS_ERROR = "#a63d3d"
COLOR_STATUS_EXPORTED = "#4a7a4a"

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
        "status": "IDLE",
        "stems_discovered": False,
        "base_dir": str(_REPO_ROOT / "test_session"),
        "session_name": "my_session",
        "stems_dir": str(_REPO_ROOT / "test_session" / "stems"),
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ======================================================================
# Logic
# ======================================================================

def _discover_stems(project_dir: str, stems_dir: str):
    """Run Stage 0 only to populate session state with stem list."""
    try:
        session = SessionManager(project_dir, stems_dir)
        manifest = session.run()
        st.session_state["manifest"] = manifest
        st.session_state["stems_discovered"] = True
        st.session_state["status"] = "READY"
        # Reset stale data
        st.session_state["classifications"] = None
        st.session_state["results"] = None
        return True
    except Exception as exc:
        st.session_state["status"] = "ERROR"
        st.error(f"Discovery failed: {exc}")
        return False


# ======================================================================
# Main UI
# ======================================================================

def main():
    """Streamlit UI entry point."""
    st.set_page_config(
        page_title="SpatialSeed Authoring",
        layout="wide",
        initial_sidebar_state="collapsed", # Usually collapsed for professional tool feel
    )

    _init_state()

    # Injected CSS for Spatial Root aesthetic
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&display=swap');

    /* Global Overrides */
    .stApp {{
        background-color: {COLOR_DARK_BG} !important;
        color: {COLOR_TEXT_LIGHT} !important;
        font-family: 'JetBrains Mono', 'Source Code Pro', monospace !important;
    }}

    /* Main Container Padding */
    .main .block-container {{
        padding-top: 2rem !important;
        max-width: 1200px !important;
    }}

    /* Typography */
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        font-family: 'JetBrains Mono', 'Source Code Pro', monospace !important;
    }}

    h1, h2, h3 {{
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 500 !important;
    }}

    /* Panels / Cards */
    .sp-card {{
        background-color: {COLOR_PARCHMENT} !important;
        color: {COLOR_TEXT_DARK} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 2px !important;
        padding: 1.25rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }}

    .sp-card-light {{
        background-color: {COLOR_PARCHMENT_LIGHT} !important;
        border: 1px solid {COLOR_BORDER} !important;
        color: {COLOR_TEXT_DARK} !important;
        padding: 0.75rem !important;
        margin-bottom: 0.5rem !important;
    }}

    /* Section Labels */
    .sp-label {{
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
        color: {COLOR_ACCENT} !important;
        margin-bottom: 0.4rem !important;
        display: block !important;
        letter-spacing: 0.1em !important;
    }}

    /* Status Indicator */
    .sp-status-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid {COLOR_ACCENT};
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }}

    .sp-status-indicator {{
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border: 1px solid {COLOR_ACCENT};
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}

    /* Tab row styling */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 1px solid {COLOR_ACCENT} !important;
        gap: 0.5rem !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: transparent !important;
        color: {COLOR_TEXT_LIGHT} !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        border-bottom: 2px solid {COLOR_PARCHMENT} !important;
        font-weight: 600 !important;
    }}

    /* Buttons */
    .stButton button {{
        background-color: {COLOR_PARCHMENT} !important;
        color: {COLOR_TEXT_DARK} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 2px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        padding: 0.4rem 1rem !important;
        transition: all 0.1s ease !important;
    }}

    .stButton button:hover {{
        background-color: {COLOR_BORDER} !important;
        border-color: {COLOR_ACCENT} !important;
    }}

    /* Inputs */
    .stTextInput input, .stSelectbox select, .stSlider {{
        background-color: rgba(255,255,255,0.05) !important;
        color: {COLOR_TEXT_LIGHT} !important;
        border: 1px solid {COLOR_ACCENT} !important;
        border-radius: 0px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
    }}

    /* Slider specific */
    .stSlider > div [data-baseweb="slider"] {{
        height: 4px !important;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {COLOR_DARK_BG}; }}
    ::-webkit-scrollbar-thumb {{ background: {COLOR_ACCENT}; border-radius: 3px; }}

    /* Hide default elements */
    #MainMenu, footer {{ display: none !important; }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-size: 1.4rem !important;
        font-weight: 500 !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.7rem !important;
        text-transform: uppercase !important;
    }}

    /* Overriding Streamlit's white background for some elements */
    .stSelectbox div[data-baseweb="select"] {{
        background-color: rgba(255,255,255,0.05) !important;
    }}
    
    /* Table styling for dark theme */
    .stTable {{
        background-color: {COLOR_DARK_BG} !important;
        color: {COLOR_TEXT_LIGHT} !important;
        border: 1px solid {COLOR_ACCENT} !important;
    }}
    .stTable th {{
        background-color: rgba(255,255,255,0.1) !important;
        color: {COLOR_TEXT_LIGHT} !important;
        border: 1px solid {COLOR_ACCENT} !important;
    }}
    .stTable td {{
        border: 1px solid {COLOR_ACCENT} !important;
    }}

    </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    status = st.session_state["status"]
    status_color = {
        "IDLE": COLOR_STATUS_IDLE,
        "READY": COLOR_STATUS_READY,
        "RUNNING": COLOR_STATUS_RUNNING,
        "ERROR": COLOR_STATUS_ERROR,
        "EXPORTED": COLOR_STATUS_EXPORTED,
    }.get(status, COLOR_STATUS_IDLE)

    st.markdown(f"""
    <div class="sp-status-bar">
        <div>
            <span style="font-size: 1.2rem; font-weight: 600; letter-spacing: 0.1em;">SPATIAL SEED</span>
            <span style="font-size: 0.7rem; color: {COLOR_ACCENT}; margin-left: 1rem; vertical-align: middle;">STEMS &rarr; MIR &rarr; SEED MATRIX &rarr; LUSID / ADM</span>
        </div>
        <div class="sp-status-indicator" style="background-color: {status_color}; border-color: {status_color}; color: white;">
            {status}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- TABS ---
    tab_author, tab_analyze, tab_export, tab_results, tab_logs = st.tabs([
        "AUTHOR", "ANALYZE", "EXPORT", "RESULTS", "LOGS"
    ])

    # 1. AUTHOR TAB
    with tab_author:
        col_input, col_matrix = st.columns([1, 1])

        with col_input:
            st.markdown('<div class="sp-card">', unsafe_allow_html=True)
            st.markdown('<span class="sp-label">Input Configuration</span>', unsafe_allow_html=True)
            
            st.session_state["base_dir"] = st.text_input("Base Output Directory", st.session_state["base_dir"])
            st.session_state["session_name"] = st.text_input("Session Name", st.session_state["session_name"])
            st.session_state["stems_dir"] = st.text_input("Stems Directory", st.session_state["stems_dir"])
            
            project_dir = str(Path(st.session_state["base_dir"]) / st.session_state["session_name"])
            st.caption(f"Full Project Path: {project_dir}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("DISCOVER STEMS", use_container_width=True):
                _discover_stems(project_dir, st.session_state["stems_dir"])
            
            st.markdown('</div>', unsafe_allow_html=True)

        with col_matrix:
            st.markdown('<div class="sp-card">', unsafe_allow_html=True)
            st.markdown('<span class="sp-label">Seed Matrix Controls</span>', unsafe_allow_html=True)
            
            u = st.slider("u — Aesthetic Variation", 0.0, 1.0, 0.5, 0.01)
            v = st.slider("v — Dynamic Immersion", 0.0, 1.0, 0.3, 0.01)
            
            st.markdown(f'<div style="font-size: 0.7rem; text-align: right; color: {COLOR_ACCENT};">CURRENT SELECTION: {u:.2f}, {v:.2f}</div>', unsafe_allow_html=True)
            
            # Interactive Canvas
            df = pd.DataFrame({"u": [u], "v": [v], "label": ["Current"]})
            chart = alt.Chart(df).mark_circle(size=200, color=COLOR_ACCENT).encode(
                x=alt.X("u:Q", scale=alt.Scale(domain=[0, 1])),
                y=alt.Y("v:Q", scale=alt.Scale(domain=[0, 1])),
            ).properties(height=200).configure_axis(
                grid=True, domain=False, labelFontSize=8, titleFontSize=8
            ).configure_view(stroke=COLOR_BORDER)
            st.altair_chart(chart, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    # 2. ANALYZE TAB
    with tab_analyze:
        st.markdown('<div class="sp-card">', unsafe_allow_html=True)
        st.markdown('<span class="sp-label">Classification / Stems</span>', unsafe_allow_html=True)
        
        manifest = st.session_state.get("manifest")
        if manifest:
            stems = manifest["stems"]
            results = st.session_state.get("results")
            overrides = st.session_state.get("overrides", {})
            
            for i, stem in enumerate(stems):
                st.markdown(f'<div class="sp-card-light">', unsafe_allow_html=True)
                cols = st.columns([2, 1, 1, 1])
                cols[0].markdown(f"**{stem['filename']}**")
                cols[1].markdown(f"SR: {stem['sample_rate']}")
                cols[2].markdown(f"CH: {stem['channels']}")
                cols[3].markdown(f"DUR: {stem['duration_seconds']:.1f}s")
                
                # Show classification if available
                if results and "classifications" in results:
                    cls_data = results["classifications"]
                    for nid in stem["node_ids"]:
                        c = cls_data.get(nid, {})
                        st.markdown(f'<div style="font-size: 0.75rem; color: {COLOR_ACCENT}; padding-left: 1rem;">'
                                    f'{nid}: {c.get("category", "?")} ({c.get("role_hint", "?")})'
                                    f'</div>', unsafe_allow_html=True)
                
                # Override inputs
                with st.expander("Overrides", expanded=False):
                    for nid in stem["node_ids"]:
                        o_cols = st.columns(2)
                        current_cat = overrides.get(nid, {}).get("category", "auto")
                        current_role = overrides.get(nid, {}).get("role_hint", "auto")
                        
                        cat_opts = ["auto"] + CATEGORIES
                        role_opts = ["auto"] + ROLES
                        
                        new_cat = o_cols[0].selectbox(f"Cat {nid}", cat_opts, index=cat_opts.index(current_cat) if current_cat in cat_opts else 0)
                        new_role = o_cols[1].selectbox(f"Role {nid}", role_opts, index=role_opts.index(current_role) if current_role in role_opts else 0)
                        
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
        else:
            st.info("DISCOVER STEMS in the AUTHOR tab to populate this list.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. EXPORT TAB
    with tab_export:
        st.markdown('<div class="sp-card">', unsafe_allow_html=True)
        st.markdown('<span class="sp-label">Export Controls</span>', unsafe_allow_html=True)
        
        export_adm = st.checkbox("Export ADM BWF (Integrated Transcoder)", value=True)
        
        col_run1, col_run2 = st.columns(2)
        if col_run1.button("GENERATE LUSID PACKAGE", use_container_width=True, disabled=not st.session_state["stems_discovered"]):
            st.session_state["status"] = "RUNNING"
            # Actual run logic
            try:
                project_dir = str(Path(st.session_state["base_dir"]) / st.session_state["session_name"])
                pipeline = SpatialSeedPipeline(project_dir=project_dir, stems_dir=st.session_state["stems_dir"])
                
                # Capture log
                old_stdout = sys.stdout
                capture = StringIO()
                sys.stdout = capture
                
                results = pipeline.run(u=u, v=v, export_adm=export_adm, 
                                       classification_overrides=st.session_state["overrides"])
                
                sys.stdout = old_stdout
                st.session_state["run_log"] = capture.getvalue()
                st.session_state["results"] = results
                st.session_state["status"] = "EXPORTED"
            except Exception as exc:
                sys.stdout = old_stdout
                st.session_state["status"] = "ERROR"
                st.error(f"Pipeline error: {exc}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sp-label">Export Status</span>', unsafe_allow_html=True)
        results = st.session_state.get("results")
        if results:
            st.success(f"LUSID Package: {results.get('lusid_package')}")
            # ADM check
            pkg_parent = Path(results.get("lusid_package")).parent
            adm_path = pkg_parent / "export.adm.wav"
            if adm_path.exists():
                st.info(f"ADM BWF: {adm_path}")
        else:
            st.write("NO EXPORT DATA")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. RESULTS TAB
    with tab_results:
        results = st.session_state.get("results")
        if results:
            col_sum, col_style = st.columns([1, 1])
            
            with col_sum:
                st.markdown('<div class="sp-card">', unsafe_allow_html=True)
                st.markdown('<span class="sp-label">Spatial Summary</span>', unsafe_allow_html=True)
                kf = results.get("keyframe_stats", {})
                m1, m2 = st.columns(2)
                m1.metric("Objects", kf.get("total_objects", 0))
                m2.metric("Keyframes", kf.get("total_keyframes", 0))
                
                m3, m4 = st.columns(2)
                m3.metric("Static", kf.get("static_objects", 0))
                m4.metric("Animated", kf.get("animated_objects", 0))
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col_style:
                st.markdown('<div class="sp-card">', unsafe_allow_html=True)
                st.markdown('<span class="sp-label">Style Vector (z)</span>', unsafe_allow_html=True)
                z = results.get("style_vector", [])
                dim_names = ["WIDTH", "HEIGHT", "DEPTH", "MOTION_I", "MOTION_C", "MOTION_P", "REACTIVE", "BRIGHT"]
                if z:
                    for name, val in zip(dim_names, z):
                        st.markdown(f'<div style="display: flex; justify-content: space-between; font-size: 0.75rem; border-bottom: 1px solid rgba(0,0,0,0.1); margin-bottom: 2px;">'
                                    f'<span>{name}</span><span>{val:.2f}</span></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="sp-card">', unsafe_allow_html=True)
            st.markdown('<span class="sp-label">Spatial Preview (Top View)</span>', unsafe_allow_html=True)
            placements = results.get("placements", {})
            if placements:
                p_df = pd.DataFrame([{"node": nid, "x": pos[0], "y": pos[1]} for nid, pos in placements.items()])
                p_chart = alt.Chart(p_df).mark_circle(size=100, color=COLOR_ACCENT).encode(
                    x=alt.X("x:Q", scale=alt.Scale(domain=[-1, 1]), title="X (Left/Right)"),
                    y=alt.Y("y:Q", scale=alt.Scale(domain=[-1, 1]), title="Y (Front/Back)"),
                    tooltip=["node", "x", "y"]
                ).properties(height=400).configure_axis(
                    grid=True, domain=False, labelFontSize=8, titleFontSize=8
                ).configure_view(stroke=COLOR_BORDER)
                st.altair_chart(p_chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="sp-card">', unsafe_allow_html=True)
            st.markdown('<span class="sp-label">Placement Summary</span>', unsafe_allow_html=True)
            if placements:
                rows = []
                for nid, pos in placements.items():
                    rows.append({"NODE": nid, "X": f"{pos[0]:.3f}", "Y": f"{pos[1]:.3f}", "Z": f"{pos[2]:.3f}"})
                st.table(rows)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("RUN GENERATE in the EXPORT tab to see results.")

    # 5. LOGS TAB
    with tab_logs:
        st.markdown('<div class="sp-card">', unsafe_allow_html=True)
        st.markdown('<span class="sp-label">Pipeline Log</span>', unsafe_allow_html=True)
        log = st.session_state.get("run_log", "")
        if log:
            st.code(log, language="text")
        else:
            st.write("NO LOG DATA")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
