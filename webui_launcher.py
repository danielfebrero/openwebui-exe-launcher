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
# Try multiple methods to run open-webui
def run_via_cli():
    """Run open-webui using its CLI interface"""
    import runpy

    # This runs the module as if invoked with: python -m open_webui
    runpy.run_module("open_webui", run_name="__main__")


try:
    from open_webui.__main__ import main as openwebui_main

    main_func = openwebui_main
    print("[WebUI Init] Successfully imported open_webui.__main__.main")
except ImportError as e:
    print(f"[WebUI Init] Could not import open_webui.__main__.main: {e}")
    # Use the CLI runner as fallback
    main_func = run_via_cli


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
    print(f"[WebUI Child] Python executable: {sys.executable}")
    print(f"[WebUI Child] Python version: {sys.version}")

    # Set default arguments for open-webui serve
    sys.argv = ["open-webui", "serve", "--port", port, "--host", host]
    print(f"[WebUI Child] Command args: {sys.argv}")

    try:
        if main_func is None:
            raise RuntimeError("No webui entry point found")
        print(f"[WebUI Child] Calling main_func...")
        sys.stdout.flush()

        # Call the main function - it should block and run the server
        result = main_func()

        # If we get here, the server exited unexpectedly
        print(f"[WebUI Child] main_func returned unexpectedly with result: {result}")
        sys.stdout.flush()

        # Exit with error code since the server shouldn't exit
        sys.exit(1)

    except SystemExit as e:
        # If open-webui calls sys.exit, re-raise it
        print(f"[WebUI Child] SystemExit caught: {e.code}")
        sys.stdout.flush()
        raise
    except KeyboardInterrupt:
        print(f"[WebUI Child] Interrupted by user")
        sys.stdout.flush()
        sys.exit(0)
    except Exception as e:
        print(f"[WebUI Child] ERROR: Open WebUI failed to start: {e}")
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    run_webui_server()
