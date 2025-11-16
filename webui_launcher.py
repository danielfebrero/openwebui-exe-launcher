#!/usr/bin/env python3
"""Portable launcher for Open WebUI.

This script is bundled with PyInstaller and is responsible for
invoking the official ``open-webui`` CLI entry point inside the
frozen environment.
"""

import os
import sys

from typing import Any


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

    try:
        # Set default arguments for open-webui serve and invoke the
        # package's CLI entry point. This mirrors running
        # ``open-webui serve --port ... --host ...`` from the shell,
        # but works inside the frozen bundle.
        sys.argv = ["open-webui", "serve", "--port", port, "--host", host]
        print(f"[WebUI Child] Command args: {sys.argv}")
        sys.stdout.flush()
        from open_webui.__main__ import main

        main()

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
