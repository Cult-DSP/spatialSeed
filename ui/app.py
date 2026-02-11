"""
SpatialSeed Streamlit UI
=========================
Minimal local web UI for SpatialSeed authoring.

Per spec: DesignSpecV1.md § 6, agents.md § 13

Features:
- Seed Matrix control (u, v)
- Stem list + category/role overrides
- Generate + export buttons
- Preview and diagnostics (optional)
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline import SpatialSeedPipeline


def main():
    """
    Streamlit UI entry point.
    """
    st.set_page_config(
        page_title="SpatialSeed",
        page_icon="🌱",
        layout="wide",
    )
    
    st.title("🌱 SpatialSeed")
    st.subheader("Immersive Spatial Scene Authoring")
    
    # Sidebar: Project settings
    with st.sidebar:
        st.header("Project Settings")
        
        project_dir = st.text_input("Project Directory", value=".")
        stems_dir = st.text_input("Stems Directory", value="stems")
        
        st.divider()
        
        st.header("Seed Matrix")
        st.write("Control the aesthetic and motion characteristics")
        
        # Seed Matrix sliders
        u = st.slider(
            "u - Aesthetic Variation",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="0 = conservative, 1 = experimental"
        )
        
        v = st.slider(
            "v - Dynamic Immersion",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            help="0 = static, 1 = enveloping/animated"
        )
        
        # Display selected point
        st.write(f"Selected: (u={u:.2f}, v={v:.2f})")
        
        st.divider()
        
        st.header("Export Options")
        export_adm = st.checkbox("Export ADM/BW64", value=False)
    
    # Main area: Tabs
    tab1, tab2, tab3 = st.tabs(["Generate", "Stems", "Results"])
    
    with tab1:
        st.header("Generate Spatial Scene")
        
        st.write("""
        Click the button below to run the complete SpatialSeed pipeline:
        
        1. **Session + Discovery** - Discover and validate stems
        2. **Normalize Audio** - Resample to 48 kHz, split stereo
        3. **MIR Extraction** - Extract music information features
        4. **Classification** - Classify instruments and assign roles
        5. **SPF Resolution** - Generate spatial style profiles
        6. **Placement** - Compute static positions
        7. **Gesture Generation** - Create motion keyframes
        8. **LUSID Scene** - Assemble scene.lusid.json
        9. **Export** - Create LUSID package (+ optional ADM/BW64)
        """)
        
        if st.button("🚀 Generate Scene", type="primary"):
            with st.spinner("Running pipeline..."):
                try:
                    # TODO: Run pipeline
                    # pipeline = SpatialSeedPipeline(project_dir, stems_dir)
                    # results = pipeline.run(u=u, v=v, export_adm=export_adm)
                    
                    st.success("✅ Pipeline complete!")
                    st.write("Results will appear in the Results tab")
                    
                    # TODO: Display results summary
                    
                except Exception as e:
                    st.error(f"❌ Pipeline failed: {e}")
                    st.exception(e)
    
    with tab2:
        st.header("Stems")
        
        st.write("""
        View discovered stems and override classifications if needed.
        
        *Note: Stem discovery and classification override UI coming soon.*
        """)
        
        # TODO: Display stem list
        # TODO: Allow user to override category/role per stem
        # TODO: Show MIR features
    
    with tab3:
        st.header("Results")
        
        st.write("""
        View pipeline results, keyframe statistics, and export locations.
        
        *Note: Results display coming soon.*
        """)
        
        # TODO: Display results from last run
        # TODO: Show keyframe stats
        # TODO: Show export paths
        # TODO: Optional: preview visualization


if __name__ == "__main__":
    main()
