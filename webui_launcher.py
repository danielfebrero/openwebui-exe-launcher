#!/usr/bin/env python3
"""
Launcher script for Open WebUI - used by the portable executable.
This script is bundled with PyInstaller to enable open-webui execution.
"""
import sys
import os

# Ensure open-webui can be imported
try:
    from open_webui.__main__ import main
except ImportError as e:
    print(f"ERROR: Failed to import open-webui: {e}")
    print("Make sure open-webui is installed: pip install open-webui")
    sys.exit(1)


def run_webui_server():
    """Launch Open WebUI with sane defaults for the portable bundle."""
    port = os.environ.get("OPENWEBUI_PORT", "3000")
    host = os.environ.get("OPENWEBUI_HOST", "0.0.0.0")

    # Set default arguments for open-webui serve
    sys.argv = ["open-webui", "serve", "--port", port, "--host", host]

    try:
        main()
    except Exception as e:
        print(f"ERROR: Open WebUI failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_webui_server()
