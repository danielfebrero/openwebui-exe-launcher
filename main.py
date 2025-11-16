import os
import sys
import subprocess
import webbrowser
import threading
import time
import socket
import atexit
import signal
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
        # Running as compiled exe
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script
        base_path = Path(__file__).parent
    return str(base_path / filename)


def get_app_dir():
    """Get application directory (USB drive location for portable mode)."""
    if getattr(sys, "frozen", False):
        # Portable mode: use exe's directory
        return Path(sys.executable).parent
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
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
    if sys.platform == "win32":
        return get_bundled_path("ollama.exe")
    return get_bundled_path("ollama")


def run_webui_child_mode():
    """Run Open WebUI inside the current process when invoked as a child."""
    try:
        from webui_launcher import run_webui_server
    except ImportError as exc:
        raise RuntimeError(
            "Failed to import bundled WebUI launcher."
        ) from exc

    run_webui_server()


def run_ollama():
    """Start Ollama server with portable data directory."""
    global ollama_process

    # Check if port is already in use
    if is_port_in_use(11434):
        raise RuntimeError(
            "Port 11434 is already in use. Another Ollama instance may be running.\n"
            "Please close it and try again."
        )

    # Setup portable directories on USB drive
    app_dir = get_app_dir()
    ollama_dir = app_dir / ".ollama"
    models_dir = ollama_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Configure Ollama to use portable directories
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(models_dir)
    # Disable debug for production (set to "1" to enable GPU/CPU logs)
    env["OLLAMA_DEBUG"] = "0"

    ollama_binary = get_ollama_binary()
    if not Path(ollama_binary).exists():
        raise FileNotFoundError(
            f"Ollama binary not found at: {ollama_binary}\n"
            f"Ensure the build process bundled the correct file."
        )

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
    for attempt in range(60):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                print("Ollama API is ready!")
                return ollama_process
        except (requests.RequestException, ConnectionError):
            pass

        # Check if process crashed
        if ollama_process.poll() is not None:
            raise RuntimeError(
                "Ollama process terminated unexpectedly. "
                "See console output for details."
            )

        time.sleep(1)

    raise RuntimeError(
        "Ollama failed to start within 60 seconds.\n"
        "Check if port 11434 is blocked by firewall or antivirus."
    )


def run_webui():
    """Start Open WebUI server with portable data directory."""
    global webui_process

    # Check if port is already in use
    if is_port_in_use(3000):
        raise RuntimeError(
            "Port 3000 is already in use. Please close the application using it."
        )

    # Setup portable data directory on USB drive
    app_dir = get_app_dir()
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Configure Open WebUI
    env = os.environ.copy()
    env["DATA_DIR"] = str(data_dir)
    env["OLLAMA_API_BASE"] = "http://localhost:11434"

    print(f"Data directory: {data_dir}")
    print("Starting Open WebUI...")

    # Ensure bundled launcher exists before spawning child process
    webui_script = get_bundled_path("webui_launcher.py")
    if not Path(webui_script).exists():
        raise FileNotFoundError(
            f"WebUI launcher not found at: {webui_script}\n"
            f"Build process may be incomplete."
        )

    try:
        webui_process = subprocess.Popen(
            build_self_command([WEBUI_CHILD_FLAG]),
            env=env,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start WebUI process: {e}")

    # Wait for WebUI to be ready
    print("Waiting for WebUI to start...")
    for attempt in range(30):
        try:
            response = requests.get("http://localhost:3000", timeout=1)
            if response.status_code in (
                200,
                404,
                302,
            ):  # Any response means it's running
                print("WebUI is ready!")
                return webui_process
        except (requests.RequestException, ConnectionError):
            pass

        # Check if process crashed
        if webui_process.poll() is not None:
            raise RuntimeError(
                "WebUI process terminated unexpectedly. "
                "See console output for details."
            )

        time.sleep(1)

    raise RuntimeError(
        "WebUI failed to start within 30 seconds.\n" "Check if port 3000 is blocked."
    )


def open_browser_delayed():
    """Open browser after ensuring WebUI is fully ready."""
    time.sleep(3)
    print("Opening browser...")
    webbrowser.open("http://localhost:3000")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\nShutting down gracefully...")
    cleanup_processes()
    sys.exit(0)


def launcher_main():
    """Primary entry point for the portable launcher."""
    # Register cleanup handlers
    atexit.register(cleanup_processes)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("=" * 50)
        print("Open WebUI + Ollama Portable Launcher")
        print("=" * 50)

        # Start services
        ollama_p = run_ollama()
        webui_p = run_webui()

        # Open browser in background
        threading.Thread(target=open_browser_delayed, daemon=True).start()

        print("\nServices running!")
        print("Access WebUI at: http://localhost:3000")
        print("Press Ctrl+C to stop\n")

        # Wait for WebUI process (main process)
        webui_p.wait()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        cleanup_processes()
        print("Shutdown complete.")


if __name__ == "__main__":
    if WEBUI_CHILD_FLAG in sys.argv:
        sys.argv.remove(WEBUI_CHILD_FLAG)
        try:
            run_webui_child_mode()
        except Exception as exc:
            print(f"\nERROR: {exc}")
            sys.exit(1)
    else:
        launcher_main()
