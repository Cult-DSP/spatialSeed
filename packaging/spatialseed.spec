# -*- mode: python ; coding: utf-8 -*-
import os
import streamlit
from pathlib import Path

# Get streamlit directory to include its resources
streamlit_dir = os.path.dirname(streamlit.__file__)

block_cipher = None

# Resolve repo root relative to this spec file
# Assuming this file is in packaging/
repo_root = Path('.').resolve().parent

a = Analysis(
    ['run_spatialseed_app.py'],
    pathex=[str(repo_root)],
    binaries=[
        (str(repo_root / 'cult_transcoder' / 'build' / 'cult-transcoder'), '.'),
    ],
    datas=[
        (str(repo_root / 'ui' / 'app.py'), 'ui'),
        (str(repo_root / 'LUSID' / 'SCHEMA' / '*.json'), 'LUSID/SCHEMA'),
        (str(repo_root / 'config' / 'defaults.json'), 'config'),
        (streamlit_dir, 'streamlit'), # Include streamlit resources
    ],
    hiddenimports=[
        'streamlit',
        'librosa',
        'soundfile',
        'numpy',
        'scipy',
        'altair',
        'pandas',
        'jsonschema',
        'pkg_resources.py2_warn', # Often needed for some older deps
        'sklearn.utils._cython_blas', # If any dep uses sklearn internally
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
        'sklearn.tree._utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpatialSeed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpatialSeed',
)
