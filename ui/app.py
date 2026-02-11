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

# ---------------------------------------------------------------------------
# Ensure src/ is importable regardless of how streamlit launches
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline import SpatialSeedPipeline
from src.session import SessionManager
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
        st.header("Project Settings")

        project_dir = st.text_input(
            "Project Directory",
            value=str(_REPO_ROOT / "test_session"),
            help="Root directory for session work/cache/export folders",
        )
        stems_dir = st.text_input(
            "Stems Directory",
            value=str(_REPO_ROOT / "test_session" / "stems"),
            help="Folder containing input stereo WAV stems",
        )

        st.divider()
        st.header("Seed Matrix")
        st.caption("Control aesthetic and motion characteristics")

        u = st.slider(
            "u -- Aesthetic Variation",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.01,
            help="0 = conservative / centred, 1 = experimental / wide",
        )
        v = st.slider(
            "v -- Dynamic Immersion",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.01,
            help="0 = mostly static, 1 = enveloping / animated",
        )

        st.code(f"(u={u:.2f}, v={v:.2f})", language=None)

        st.divider()
        st.caption("SpatialSeed v0.1.0")

    return project_dir, stems_dir, u, v


def _render_generate_tab(project_dir: str, stems_dir: str, u: float, v: float):
    """Render the Generate tab."""
    st.header("Generate Spatial Scene")

    # Discover / refresh stems button
    col_disc, col_gen = st.columns([1, 1])

    with col_disc:
        if st.button("Discover Stems", use_container_width=True):
            with st.spinner("Discovering stems..."):
                try:
                    _discover_stems(project_dir, stems_dir)
                    st.success(
                        f"Found {st.session_state['manifest']['stem_count']} stems "
                        f"({st.session_state['manifest']['object_count']} objects)"
                    )
                except Exception as exc:
                    st.error(f"Discovery failed: {exc}")

    with col_gen:
        generate_disabled = not st.session_state.get("stems_discovered", False)
        if st.button(
            "Generate Scene",
            type="primary",
            use_container_width=True,
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

    if generate_disabled:
        st.info("Click **Discover Stems** first to scan the stems directory.")

    # Quick reference: pipeline stages
    with st.expander("Pipeline stages reference"):
        for i, name in enumerate([
            "Session + Discovery",
            "Normalize + Split Audio (48 kHz, stereo split, bed generation)",
            "MIR Feature Extraction (librosa)",
            "Classification + Role Assignment",
            "Seed Matrix Selection (u,v) -> style vector z",
            "SPF Resolution -> StyleProfile per object",
            "Static Placement (Cartesian cube)",
            "Gesture Generation (sparse keyframes)",
            "LUSID Scene Assembly (scene.lusid.json)",
            "LUSID Package Export (containsAudio.json, WAV copy)",
        ]):
            st.write(f"**Stage {i}:** {name}")


def _render_stems_tab():
    """Render the Stems tab with classification overrides."""
    st.header("Stems + Classification Overrides")

    manifest = st.session_state.get("manifest")
    if manifest is None:
        st.info("No stems discovered yet. Go to the **Generate** tab and click **Discover Stems**.")
        return

    stems = manifest["stems"]

    st.write(
        f"**{len(stems)} stems** discovered "
        f"({manifest['object_count']} objects, "
        f"max duration {manifest['max_duration_seconds']:.1f}s)"
    )

    overrides = st.session_state.get("overrides", {})
    results = st.session_state.get("results")

    # Build a row per stem
    for i, stem in enumerate(stems):
        with st.expander(f"Stem {i+1}: {stem['filename']}", expanded=(i < 3)):
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
                )
                new_role = c2.selectbox(
                    f"Role ({nid})",
                    options=role_options,
                    index=role_options.index(current_role) if current_role in role_options else 0,
                    key=f"role_{nid}",
                )

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

    st.session_state["overrides"] = overrides

    if overrides:
        st.divider()
        st.write("**Active overrides:**")
        for nid, ov in sorted(overrides.items()):
            parts = []
            if "category" in ov:
                parts.append(f"category={ov['category']}")
            if "role_hint" in ov:
                parts.append(f"role={ov['role_hint']}")
            st.write(f"- `{nid}`: {', '.join(parts)}")
        st.caption("Overrides are applied on the next Generate run.")


def _render_results_tab():
    """Render the Results tab."""
    st.header("Results")

    results = st.session_state.get("results")
    if results is None:
        st.info("No results yet. Run the pipeline from the **Generate** tab.")
        return

    # -- Summary metrics -----------------------------------------------
    st.subheader("Summary")
    m1, m2, m3, m4 = st.columns(4)

    kf_stats = results.get("keyframe_stats", {})
    m1.metric("Total Objects", kf_stats.get("total_objects", "?"))
    m2.metric("Total Keyframes", kf_stats.get("total_keyframes", "?"))
    m3.metric("Static Objects", kf_stats.get("static_objects", "?"))
    m4.metric("Animated Objects", kf_stats.get("animated_objects", "?"))

    st.write(
        f"Avg keyframes/object: **{kf_stats.get('avg_keyframes_per_object', '?')}**"
    )

    # -- Style vector --------------------------------------------------
    st.subheader("Style Vector")
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

    # -- Export paths --------------------------------------------------
    st.subheader("Export")
    lusid_pkg = results.get("lusid_package", "")
    if lusid_pkg:
        st.write(f"LUSID package: `{lusid_pkg}`")

        pkg_path = Path(lusid_pkg)
        if pkg_path.is_dir():
            files = sorted(pkg_path.iterdir())
            wav_count = sum(1 for f in files if f.suffix == ".wav")
            json_count = sum(1 for f in files if f.suffix == ".json")
            st.write(f"  {json_count} JSON files, {wav_count} WAV files")

    # -- Scene details -------------------------------------------------
    scene_info = results.get("scene_info")
    if scene_info:
        st.subheader("LUSID Scene")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Frames", scene_info.get("frame_count", "?"))
        sc2.metric("Audio Object Entries", scene_info.get("audio_object_entries", "?"))
        sc3.metric("Bed/LFE Entries", scene_info.get("bed_entries", "?"))

    # -- Per-object classification table --------------------------------
    cls_data = results.get("classifications")
    if cls_data:
        st.subheader("Classifications")
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

    # -- Run log -------------------------------------------------------
    run_log = st.session_state.get("run_log", "")
    if run_log:
        with st.expander("Pipeline log"):
            st.code(run_log, language="text")


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

    _init_state()

    st.title("SpatialSeed")
    st.caption("Immersive Spatial Scene Authoring  --  LUSID-first pipeline")

    project_dir, stems_dir, u, v = _render_sidebar()

    tab_gen, tab_stems, tab_results = st.tabs(["Generate", "Stems", "Results"])

    with tab_gen:
        _render_generate_tab(project_dir, stems_dir, u, v)

    with tab_stems:
        _render_stems_tab()

    with tab_results:
        _render_results_tab()


if __name__ == "__main__":
    main()
