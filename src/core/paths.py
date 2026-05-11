import sys
import os
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for development and for PyInstaller frozen mode.
    
    In development mode, it resolves paths relative to the repository root.
    In frozen mode, it resolves paths relative to sys._MEIPASS (handling _internal if present).
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
        
        # PyInstaller 6+ puts resources in an _internal folder in 'one-folder' mode
        internal_path = base_path / "_internal"
        if internal_path.exists():
            base_path = internal_path
    else:
        # In development, use repo root (assuming this file is in src/core/paths.py)
        base_path = Path(__file__).resolve().parent.parent.parent
    
    return base_path / relative_path

def get_user_data_dir() -> Path:
    """
    Get platform-specific user-writable data directory for SpatialSeed.
    
    Returns:
        - macOS: ~/Library/Application Support/SpatialSeed/
        - Windows: %APPDATA%/SpatialSeed/
        - Linux: ~/.local/share/spatialseed/
    """
    app_name = "SpatialSeed"
    
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        # Linux / Other (respect XDG_DATA_HOME if set)
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    data_dir = base / app_name
    
    # We don't necessarily want to create it here as it might be used just for path resolution,
    # but for this prototype, we ensure it exists.
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir

def get_streamlit_app_path() -> Path:
    """Returns the path to the ui/app.py file."""
    return get_resource_path("ui/app.py")

def get_cult_transcoder_path() -> Path:
    """
    Resolves cult-transcoder in this priority order:
    1. SPATIALSEED_CULT_PATH environment variable
    2. Bundled binary path in frozen mode
    3. Local development repo path
    4. System PATH fallback
    """
    # 1. Environment variable override
    env_path = os.environ.get("SPATIALSEED_CULT_PATH")
    if env_path:
        return Path(env_path)
    
    # Binary name depends on platform
    bin_name = "cult-transcoder"
    if sys.platform == "win32":
        bin_name += ".exe"
        
    # 2. Frozen mode (PyInstaller)
    # We plan to bundle it at the root of the _MEIPASS folder
    if hasattr(sys, '_MEIPASS'):
        bundled_path = Path(sys._MEIPASS) / bin_name
        if bundled_path.exists():
            return bundled_path

    # 3. Local development path
    dev_path = get_resource_path(f"cult_transcoder/build/{bin_name}")
    if dev_path.exists():
        return dev_path
        
    # 4. System PATH fallback
    return Path(bin_name)
