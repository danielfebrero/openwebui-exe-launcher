#!/usr/bin/env python3
"""
Launcher script for Open WebUI - used by the portable executable.
This script is bundled with PyInstaller to enable open-webui execution.
"""
import sys
import os
from pathlib import Path
from typing import Any

# Set frontend build directory for bundled app
if sys.platform == "darwin":
    # macOS .app bundle: executable in Contents/MacOS, build in Contents/build
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "build")
else:
    # Windows/Linux: executable and build in same directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "build")
os.environ["FRONTEND_BUILD_DIR"] = frontend_dir

main_func = None

# Open WebUI is typically run via its CLI entry point defined in pyproject.toml
# Try to find and use the proper entry point
try:
    # Try the main entry point - open-webui uses a CLI via main.py
    from open_webui.main import app

    print("[WebUI Init] Successfully imported open_webui.main.app")

    def run_uvicorn_server():
        """Run the FastAPI app using uvicorn"""
        import uvicorn

        port = int(os.environ.get("OPENWEBUI_PORT", "3000"))
        host = os.environ.get("OPENWEBUI_HOST", "127.0.0.1")

        print(f"[WebUI Init] Starting uvicorn server on {host}:{port}")
        uvicorn.run(app, host=host, port=port, log_level="info", access_log=True)

    main_func = run_uvicorn_server

except ImportError as e:
    print(f"[WebUI Init] Could not import open_webui.main.app: {e}")
    if getattr(e, "name", "") == "numpy" or "numpy" in str(e):
        print(
            "[WebUI Init] Missing dependency detected: numpy. Add it to requirements and rebuild the portable bundle."
        )

    # Fallback: try to import the app from other common locations
    try:
        from open_webui.apps.webui.main import app

        print("[WebUI Init] Successfully imported open_webui.apps.webui.main.app")

        def run_uvicorn_server():
            import uvicorn

            port = int(os.environ.get("OPENWEBUI_PORT", "3000"))
            host = os.environ.get("OPENWEBUI_HOST", "127.0.0.1")
            uvicorn.run(app, host=host, port=port, log_level="info")

        main_func = run_uvicorn_server
    except ImportError as e2:
        print(f"[WebUI Init] Could not import from apps.webui.main: {e2}")
        print("[WebUI Init] ERROR: Unable to locate open-webui application")

        # Fallback ultime : assume open-webui est installé globalement ou via sys.path
        import sys

        sys.path.insert(
            0, str(Path(__file__).parent / "open_webui")
        )  # Si bundle a un sous-dossier open_webui
        try:
            from open_webui.backend.main import (
                app,
            )  # Autre chemin possible dans certaines versions

            print("[WebUI Init] Successfully imported open_webui.backend.main.app")

            def run_uvicorn_server():
                import uvicorn

                port = int(os.environ.get("OPENWEBUI_PORT", "3000"))
                host = os.environ.get("OPENWEBUI_HOST", "127.0.0.1")
                uvicorn.run(app, host=host, port=port, log_level="info")

            main_func = run_uvicorn_server
        except ImportError as e3:
            print(f"[WebUI Init] All import attempts failed: {e3}")
            print(
                "[WebUI Init] Check if 'pip install open-webui' is needed in the bundle env."
            )


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
