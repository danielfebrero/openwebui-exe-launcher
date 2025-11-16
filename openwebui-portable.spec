# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Open WebUI + Ollama Portable Launcher
This provides more control over the build process than command-line arguments.
"""

import sys
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Determine platform-specific ollama binary
ollama_binary = 'ollama.exe' if sys.platform == 'win32' else 'ollama'

# Add data files
added_files = [
    ('webui_launcher.py', '.'),
]

# Only add ollama if it exists (allows build to fail gracefully).
# Place Ollama in binaries so PyInstaller preserves executable flags where
# possible. If the binary is not present, warn the packager.
added_binaries = []
if Path(ollama_binary).exists():
    added_binaries.append((ollama_binary, '.'))
else:
    raise SystemExit(
        f"ERROR: {ollama_binary} not found. Please place the Ollama binary next to the spec before building."
    )

# Hidden imports required by open-webui
hidden_imports = [
    'open_webui',
    'open_webui.__main__',
    'numpy',
    'uvicorn',
    'fastapi',
    'pydantic',
    'sqlalchemy',
    'sqlite3',
    'chromadb',
    'chromadb.telemetry.product.posthog',
    'langchain',
]

open_webui_datas, open_webui_binaries, open_webui_hiddenimports = collect_all('open_webui')
hidden_imports = sorted(set(hidden_imports + open_webui_hiddenimports))
datas = added_files + open_webui_datas
# Merge collected binaries with our added Ollama binary
binaries = open_webui_binaries + added_binaries

# Resolve the base path where the spec file is located. Some hosted
# environments may not set `__file__`, so we fall back to the current
# working directory if necessary. Use an inline expression to avoid
# potential parsing differences in restricted build environments.
base_path = Path(__file__).parent if '__file__' in globals() else Path.cwd()


a = Analysis(
    ['main.py'],
    # Fallback base path to ensure we can find bundled resources even when
    # __file__ isn't defined during execution in certain environments.
    pathex=[str(base_path)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'PIL',
    ],
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
    name='OpenWebUI-Ollama-Portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OpenWebUI-Ollama-Portable',
)
