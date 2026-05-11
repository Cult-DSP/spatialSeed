import os
import sys
from pathlib import Path
import streamlit.web.cli as stcli

# Add src to sys.path so we can import our core modules
# When frozen, sys._MEIPASS will be the root
if hasattr(sys, '_MEIPASS'):
    base_path = Path(sys._MEIPASS)
    # PyInstaller 6+ layout
    if (base_path / "_internal").exists():
        base_path = base_path / "_internal"
else:
    base_path = Path(__file__).resolve().parent.parent

if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

from src.core.paths import get_streamlit_app_path, get_user_data_dir

def main():
    """
    Launcher for the SpatialSeed Streamlit app.
    Runs Streamlit in-process for PyInstaller compatibility.
    """
    print("--- SpatialSeed Launcher ---")

    app_path = get_streamlit_app_path()
    if not app_path.exists():
        print(f"Error: Streamlit app not found at {app_path}")
        sys.exit(1)

    # Ensure user data dir exists
    user_data_dir = get_user_data_dir()
    print(f"User data directory: {user_data_dir}")

    # Set up streamlit arguments for stcli.main()
    # We let streamlit handle the browser opening (headless=false by default)
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.runOnSave=false",
    ]

    print(f"Launching Streamlit: {app_path}")

    try:
        # Run streamlit in-process
        stcli.main()
    except SystemExit as e:
        # Streamlit calls sys.exit(0) on normal shutdown
        if e.code != 0:
            print(f"Streamlit exited with code: {e.code}")
            raise
    except Exception as e:
        print(f"Error starting SpatialSeed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

