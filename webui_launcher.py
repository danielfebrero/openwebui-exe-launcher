#!/usr/bin/env python3
"""
Launcher script for Open WebUI - used by the portable executable.
This script is bundled with PyInstaller to enable open-webui execution.
"""
import sys
import os
from typing import Any

# `main` is a callable provided by open_webui.__main__ or a fallback
# Avoid conflicting with the `main` symbol imported from open_webui.__main__
# — use `main_func` to store a callable we can safely execute.
main_func = None

# Ensure open-webui can be imported
try:
    from open_webui.__main__ import main as openwebui_main

    main_func = openwebui_main
except ImportError:
    # Try to provide a more robust fallback so the launcher works
    # in a frozen environment where module import paths may differ.
    try:
        import importlib
        import runpy

        # Try to import open_webui top-level package and call its main if present
        pkg = importlib.import_module("open_webui")
        main_candidate = getattr(pkg, "main", None)
        if callable(main_candidate):
            main_func = main_candidate
        if not main_func:
            # As a final fallback, run the package as a module (runs __main__)
            def main():
                # runpy will respect sys.argv set below
                runpy.run_module("open_webui.__main__", run_name="__main__")

            main_func = main

    except Exception as e:
        print(f"ERROR: Failed to import or locate open-webui: {e}")
        print("Make sure open-webui is installed: pip install open-webui")
        sys.exit(1)


def run_webui_server():
    """Launch Open WebUI with sane defaults for the portable bundle."""
    import sys
    import traceback

    port = os.environ.get("OPENWEBUI_PORT", "3000")
    host = os.environ.get("OPENWEBUI_HOST", "127.0.0.1")
    data_dir = os.environ.get("DATA_DIR", "./data")

    print(f"[WebUI Child] Starting Open WebUI server...")
    print(f"[WebUI Child] Port: {port}, Host: {host}")
    print(f"[WebUI Child] Data directory: {data_dir}")
    print(f"[WebUI Child] Ollama API: {os.environ.get('OLLAMA_API_BASE', 'not set')}")

    # Set default arguments for open-webui serve
    sys.argv = ["open-webui", "serve", "--port", port, "--host", host]
    print(f"[WebUI Child] Command args: {sys.argv}")

    try:
        if main_func is None:
            raise RuntimeError("No webui entry point found")
        print(f"[WebUI Child] Calling main_func...")
        main_func()
        print(f"[WebUI Child] main_func returned (should not reach here)")
    except Exception as e:
        print(f"[WebUI Child] ERROR: Open WebUI failed to start: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_webui_server()
