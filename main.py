import os
import sys
import subprocess
import webbrowser
import threading
import time
import socket
import atexit
import signal
import logging
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests module not found. Install with: pip install requests")
    sys.exit(1)


# Global process references for cleanup
ollama_process = None
webui_process = None

WEBUI_CHILD_FLAG = "--webui-child"


def get_bundled_path(filename):
    """Get path to bundled resource, handling PyInstaller frozen state."""
    if getattr(sys, "frozen", False):
        # Running as compiled exe; use sys._MEIPASS when available. Some
        # static analyzers don't know about _MEIPASS; guard with getattr.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base_path = Path(meipass)
        else:
            # Fallback to the executable's parent if _MEIPASS isn't set.
            base_path = Path(sys.executable).parent
    else:
        # Running as script
        base_path = Path(__file__).parent
    return str(base_path / filename)


def get_app_dir():
    """Get application directory (USB drive location for portable mode)."""
    if getattr(sys, "frozen", False):
        # Portable mode: use exe's directory. For macOS .app bundles we want
        # to store user data next to the .app (outside the bundle) so it does
        # not get packaged into the application and remains writable. Walk
        # up the parent tree to find a .app folder and return its parent.
        exe_dir = Path(sys.executable).parent
        if sys.platform == "darwin":
            # Walk up to find .app; if found, return its parent directory
            p = Path(sys.executable)
            while p != p.parent:
                if p.suffix == ".app":
                    return p.parent
                p = p.parent
        return exe_dir
    return Path(__file__).parent


def build_self_command(extra_args=None):
    """Return command list that relaunches this launcher with extra args."""
    cmd = [sys.executable]
    if not getattr(sys, "frozen", False):
        cmd.append(str(Path(__file__).resolve()))

    if extra_args:
        cmd.extend(extra_args)
    return cmd


def is_port_in_use(port):
    """Check if a port is already in use."""
    # Use an explicit IPv4 localhost to avoid IPv6 resolution issues with "localhost"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def cleanup_processes():
    """Terminate all child processes cleanly."""
    global ollama_process, webui_process

    if webui_process and webui_process.poll() is None:
        try:
            webui_process.terminate()
            webui_process.wait(timeout=5)
        except Exception as e:
            print(f"Warning: WebUI cleanup failed: {e}")
            try:
                webui_process.kill()
            except:
                pass

    if ollama_process and ollama_process.poll() is None:
        try:
            ollama_process.terminate()
            ollama_process.wait(timeout=5)
        except Exception as e:
            print(f"Warning: Ollama cleanup failed: {e}")
            try:
                ollama_process.kill()
            except:
                pass


def get_ollama_binary():
    """Get platform-specific ollama binary name."""
    # Platform-specific names
    if sys.platform == "win32":
        # On Windows the packaged binary is `ollama.exe`
        return get_bundled_path("ollama.exe")

    # macOS and Linux: prefer the located bundle path but also
    # check for common alternate locations inside a macOS app bundle.
    candidates = []
    candidates.append(get_bundled_path("ollama"))

    # When packaged by PyInstaller, files may be placed in different
    # directories inside the .app bundle (Resources, Frameworks) depending
    # on the spec and platform specifics. Check common variant locations.
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(meipass)
        else:
            base = Path(sys.executable).parent

        # Try Resources and Frameworks where packaging tools may place binaries
        candidates.append(str(base / "Resources" / "ollama"))
        candidates.append(str(base.parent / "Frameworks" / "ollama"))

    # Return the first existing candidate (if any); otherwise return the
    # default bundled location to preserve existing behavior and let the
    # caller fail with a useful error if not found.
    for c in candidates:
        if Path(c).exists():
            return c

    # Default fallback
    return get_bundled_path("ollama")


def run_webui_child_mode():
    """Run Open WebUI inside the current process when invoked as a child."""
    try:
        from webui_launcher import run_webui_server
    except ImportError as exc:
        raise RuntimeError("Failed to import bundled WebUI launcher.") from exc

    run_webui_server()


def run_ollama():
    """Start Ollama server with portable data directory."""
    global ollama_process

    # Find available port starting from 11434
    ollama_port = 11434
    for port_attempt in range(11434, 11444):
        if not is_port_in_use(port_attempt):
            ollama_port = port_attempt
            break
    else:
        raise RuntimeError(
            "Ports 11434-11443 are all in use. Please close other applications and try again."
        )

    if ollama_port != 11434:
        print(f"Port 11434 in use, using alternate port {ollama_port}")

    # Setup portable directories on USB drive
    app_dir = get_app_dir()
    ollama_dir = app_dir / ".ollama"
    models_dir = ollama_dir / "models"
    cache_dir = ollama_dir / "cache"
    ollama_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Configure Ollama to use portable directories
    env = os.environ.copy()
    # Keep all Ollama state on the portable drive rather than the host machine
    env["OLLAMA_HOME"] = str(ollama_dir)
    env["OLLAMA_MODELS"] = str(models_dir)
    env["OLLAMA_CACHE"] = str(cache_dir)
    env["OLLAMA_HOST"] = f"127.0.0.1:{ollama_port}"
    # Disable debug for production (set to "1" to enable GPU/CPU logs)
    env["OLLAMA_DEBUG"] = "0"

    ollama_binary = get_ollama_binary()
    if not Path(ollama_binary).exists():
        raise FileNotFoundError(
            f"Ollama binary not found at: {ollama_binary}\n"
            f"Ensure the build process bundled the correct file."
        )

    # Ensure the binary is executable on Unix-like systems. During packaging
    # the executable permission can sometimes be lost, so set it explicitly
    # before attempting to launch Ollama.
    try:
        if sys.platform != "win32":
            Path(ollama_binary).chmod(0o755)
    except Exception as e:
        # Chmod failure is non-fatal; the subsequent subprocess call may still
        # succeed (or fail) depending on filesystem semantics — warn instead
        # of raising to avoid hiding the original error message.
        print(f"Warning: Failed to set executable permissions on {ollama_binary}: {e}")

    print(f"Starting Ollama from: {ollama_binary}")
    print(f"Models directory: {models_dir}")

    try:
        ollama_process = subprocess.Popen(
            [ollama_binary, "serve"],
            cwd=str(ollama_dir),
            env=env,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start Ollama process: {e}")

    # Wait for Ollama API to be ready
    print("Waiting for Ollama API to start...")
    ollama_url = f"http://127.0.0.1:{ollama_port}"
    for attempt in range(60):
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=1)
            if response.status_code == 200:
                print(f"Ollama API is ready at {ollama_url}!")
                # Store port for WebUI to use
                env["OLLAMA_PORT"] = str(ollama_port)
                # Make sure the running process also knows the port so the WebUI
                # launcher (spawned separately) can pick it up from the environment.
                os.environ["OLLAMA_PORT"] = str(ollama_port)
                return ollama_process
        except (requests.RequestException, ConnectionError):
            pass

        # Check if process crashed
        if ollama_process.poll() is not None:
            exit_code = ollama_process.returncode
            raise RuntimeError(
                f"Ollama process crashed during startup (exit code {exit_code}). "
                "Check console output above for error details. "
                "Common issues: GPU driver problems, insufficient permissions, or corrupted binary."
            )

        time.sleep(1)

    raise RuntimeError(
        f"Ollama failed to start within 60 seconds at {ollama_url}.\n"
        f"Check if port {ollama_port} is blocked by firewall or antivirus."
    )


def run_webui():
    """Start Open WebUI server with portable data directory."""
    global webui_process

    # Find available port starting from 3000
    webui_port = 3000
    for port_attempt in range(3000, 3010):
        if not is_port_in_use(port_attempt):
            webui_port = port_attempt
            break
    else:
        raise RuntimeError(
            "Ports 3000-3009 are all in use. Please close other applications and try again."
        )

    if webui_port != 3000:
        print(f"Port 3000 in use, using alternate port {webui_port}")

    # Setup portable data directory on USB drive
    app_dir = get_app_dir()
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Configure Open WebUI
    env = os.environ.copy()
    env["DATA_DIR"] = str(data_dir)
    # Use dynamic Ollama port from environment or default
    ollama_port = os.environ.get("OLLAMA_PORT", "11434")
    env["OLLAMA_API_BASE"] = f"http://127.0.0.1:{ollama_port}"
    env["OPENWEBUI_PORT"] = str(webui_port)
    env["OPENWEBUI_HOST"] = "127.0.0.1"

    print(f"Data directory: {data_dir}")
    print("Starting Open WebUI...")

    # Ensure bundled launcher exists before spawning child process
    webui_script = get_bundled_path("webui_launcher.py")
    if not Path(webui_script).exists():
        raise FileNotFoundError(
            f"WebUI launcher not found at: {webui_script}\n"
            f"Build process may be incomplete."
        )

    # Log the command being executed
    webui_cmd = build_self_command([WEBUI_CHILD_FLAG])
    logging.info(f"WebUI command: {' '.join(webui_cmd)}")
    logging.info(
        f"WebUI environment: DATA_DIR={env['DATA_DIR']}, OLLAMA_API_BASE={env['OLLAMA_API_BASE']}"
    )

    try:
        # Don't redirect stdout/stderr so they go to the log naturally
        webui_process = subprocess.Popen(
            webui_cmd,
            env=env,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start WebUI process: {e}")

    # Wait for WebUI to be ready
    logging.info(f"Waiting for WebUI to start on port {webui_port}...")
    webui_url = f"http://127.0.0.1:{webui_port}"
    for attempt in range(30):
        try:
            response = requests.get(webui_url, timeout=1)
            if response.status_code in (
                200,
                404,
                302,
            ):  # Any response means it's running
                print(f"WebUI is ready at {webui_url}!")
                return webui_process
        except (requests.RequestException, ConnectionError):
            pass

        # Check if process crashed
        if webui_process.poll() is not None:
            exit_code = webui_process.returncode
            error_msg = (
                f"WebUI process exited early during startup (exit code {exit_code}).\n"
                f"Check the log output above for details.\n"
                f"Common issues: missing dependencies, database errors, import failures, or Ollama connection problems."
            )
            raise RuntimeError(error_msg)

        time.sleep(1)

    raise RuntimeError(
        f"WebUI failed to start within 30 seconds at {webui_url}.\n"
        f"Check if port {webui_port} is blocked or if there are dependency issues."
    )


def open_browser_delayed(port=3000):
    """Open browser after ensuring WebUI is fully ready."""
    time.sleep(3)
    webui_url = f"http://localhost:{port}"
    print(f"Opening browser to {webui_url}...")
    webbrowser.open(webui_url)


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\nShutting down gracefully...")
    cleanup_processes()
    sys.exit(0)


def setup_logging():
    """Setup logging to file in app directory for debugging."""
    app_dir = get_app_dir()
    log_file = app_dir / "launcher.log"

    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info(f"Logging initialized. Log file: {log_file}")
    return log_file


def launcher_main():
    """Primary entry point for the portable launcher."""
    try:
        # Setup logging first
        log_file = setup_logging()
        logging.info("=" * 50)
        logging.info("Open WebUI + Ollama Portable Launcher")
        logging.info("=" * 50)
    except Exception as e:
        # If logging setup fails, at least try to print
        print(f"Failed to setup logging: {e}")
        sys.exit(1)

    # Register cleanup handlers
    atexit.register(cleanup_processes)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:

        # Start services
        logging.info("Starting Ollama...")
        ollama_p = run_ollama()

        logging.info("Starting WebUI...")
        webui_p = run_webui()

        # Get WebUI port from environment
        webui_port = int(os.environ.get("OPENWEBUI_PORT", "3000"))

        # Open browser in background
        threading.Thread(
            target=open_browser_delayed, args=(webui_port,), daemon=True
        ).start()

        logging.info("\nServices running!")
        logging.info(f"Access WebUI at: http://localhost:{webui_port}")
        ollama_port = os.environ.get("OLLAMA_PORT", "11434")
        logging.info(f"Ollama API at: http://localhost:{ollama_port}")
        logging.info("Press Ctrl+C to stop\n")
        logging.info(f"Log file available at: {log_file}")

        # Wait for WebUI process (main process)
        webui_p.wait()

    except KeyboardInterrupt:
        logging.info("\nInterrupted by user")
    except Exception as e:
        logging.error(f"\nERROR: {e}", exc_info=True)
        sys.exit(1)
    finally:
        cleanup_processes()
        logging.info("Shutdown complete.")


if __name__ == "__main__":
    if WEBUI_CHILD_FLAG in sys.argv:
        sys.argv.remove(WEBUI_CHILD_FLAG)
        try:
            run_webui_child_mode()
        except Exception as exc:
            # Log to parent's log file if possible
            try:
                app_dir = get_app_dir()
                log_file = app_dir / "launcher.log"
                with open(log_file, "a") as f:
                    f.write(f"\nWEBUI CHILD ERROR: {exc}\n")
                    import traceback

                    traceback.print_exc(file=f)
            except:
                pass
            print(f"\nERROR: {exc}")
            sys.exit(1)
    else:
        launcher_main()
