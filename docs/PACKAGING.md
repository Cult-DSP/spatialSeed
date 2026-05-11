# SpatialSeed Packaging

This document describes the packaging architecture and build process for the SpatialSeed prototype.

## Architecture

SpatialSeed is packaged using **PyInstaller**. Since it is a Streamlit application, the packaging involves several layers:

1.  **Launcher:** `packaging/run_spatialseed_app.py` acts as the entry point. It programmatically starts the Streamlit server and opens the browser.
2.  **Resource Resolution:** A centralized helper in `src/core/paths.py` handles path resolution using `sys._MEIPASS` when running in "frozen" mode.
3.  **User Data Isolation:** The packaged app is designed to be read-only. All generated project files, cache, and logs are stored in platform-appropriate user-writable directories:
    - **macOS:** `~/Library/Application Support/SpatialSeed/`
    - **Linux:** `~/.local/share/spatialseed/`
    - **Windows:** `%APPDATA%/SpatialSeed/`
4.  **Bundled Binaries:** The `cult-transcoder` binary is bundled directly within the application package and resolved at runtime.

## Prerequisites

- Python 3.9+ with a configured virtual environment.
- **CULT Transcoder** must be built locally:
    ```bash
    cd cult_transcoder
    cmake -B build
    cmake --build build
    ```
- **PyInstaller** (installed automatically by the build script if missing).

## Build Instructions

### macOS

Run the build script:
```bash
./packaging/build_macos.sh
```

The output will be generated in `packaging/dist/SpatialSeed/`.

### Linux

(Prototype script coming soon, similar to macOS).

## Running the Packaged App

Navigate to the output directory and run the executable:
```bash
cd packaging/dist/SpatialSeed
./SpatialSeed
```

## Known Limitations (Prototype)

- **Signing & Notarization:** The macOS app is not signed or notarized. You may need to allow it in System Settings > Privacy & Security.
- **Single-Folder Mode:** This prototype uses "one-folder" mode for easier debugging. "One-file" mode is deferred.
- **Streamlit Startup:** There is a short delay (approx. 2 seconds) between launching the app and the browser opening.
- **Console Window:** The app currently opens a console window to display logs.

## Troubleshooting

- **Missing Binary:** If `cult-transcoder` is not found, ensure it was built before running the build script.
- **Module Errors:** If a "ModuleNotFoundError" occurs, ensure `hiddenimports` in `spatialseed.spec` is up to date.
- **Read-only Errors:** Ensure the app is not trying to write into its own bundle. Check `src/core/paths.py` and `ui/app.py` logic.
