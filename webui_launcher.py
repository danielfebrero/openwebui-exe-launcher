#!/usr/bin/env python3
"""
Launcher script for Open WebUI - used by the portable executable.
This script is bundled with PyInstaller to enable open-webui execution.
"""
import sys
import os
from typing import Any

main: Any = None

# Ensure open-webui can be imported
try:
    from open_webui.__main__ import main
except ImportError:
    # Try to provide a more robust fallback so the launcher works
    # in a frozen environment where module import paths may differ.
    try:
        import importlib
        import runpy

        # Try to import open_webui top-level package and call its main if present
        pkg = importlib.import_module("open_webui")
        main = getattr(pkg, "main", None)
        if not main:
            # As a final fallback, run the package as a module (runs __main__)
            def main():
                # runpy will respect sys.argv set below
                runpy.run_module("open_webui.__main__", run_name="__main__")

    except Exception as e:
        print(f"ERROR: Failed to import or locate open-webui: {e}")
        print("Make sure open-webui is installed: pip install open-webui")
        sys.exit(1)


def run_webui_server():
    """Launch Open WebUI with sane defaults for the portable bundle."""
    port = os.environ.get("OPENWEBUI_PORT", "3000")
    host = os.environ.get("OPENWEBUI_HOST", "127.0.0.1")

    # Set default arguments for open-webui serve
    sys.argv = ["open-webui", "serve", "--port", port, "--host", host]

    try:
        main()
    except Exception as e:
        print(f"ERROR: Open WebUI failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_webui_server()
