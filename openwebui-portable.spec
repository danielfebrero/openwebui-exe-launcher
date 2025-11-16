# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Open WebUI + Ollama Portable Launcher
This provides more control over the build process than command-line arguments.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Determine platform-specific ollama binary
ollama_binary = 'ollama.exe' if sys.platform == 'win32' else 'ollama'

# Add data files
added_files = [
    ('webui_launcher.py', '.'),
]

# Only add ollama if it exists (allows build to fail gracefully)
if Path(ollama_binary).exists():
    added_files.append((ollama_binary, '.'))
else:
    print(f"WARNING: {ollama_binary} not found. Build will fail at runtime!")

# Hidden imports required by open-webui
hidden_imports = [
    'open_webui',
    'open_webui.__main__',
    'uvicorn',
    'fastapi',
    'pydantic',
    'sqlalchemy',
    'sqlite3',
    'chromadb',
    'langchain',
]

open_webui_datas, open_webui_binaries, open_webui_hiddenimports = collect_all('open_webui')
hidden_imports = sorted(set(hidden_imports + open_webui_hiddenimports))
datas = added_files + open_webui_datas
binaries = open_webui_binaries

a = Analysis(
    ['main.py'],
    pathex=[str(Path(__file__).parent)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
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
