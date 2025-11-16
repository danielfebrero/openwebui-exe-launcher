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

if __name__ == "__main__":
    # Set default arguments for open-webui serve
    sys.argv = ["open-webui", "serve", "--port", "3000", "--host", "0.0.0.0"]

    # Run open-webui
    try:
        main()
    except Exception as e:
        print(f"ERROR: Open WebUI failed to start: {e}")
        sys.exit(1)
