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
    if sys.platform == "win32":
        return get_bundled_path("ollama.exe")
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

    try:
        webui_process = subprocess.Popen(
            build_self_command([WEBUI_CHILD_FLAG]),
            env=env,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start WebUI process: {e}")

    # Wait for WebUI to be ready
    print(f"Waiting for WebUI to start on port {webui_port}...")
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
            raise RuntimeError(
                f"WebUI process crashed during startup (exit code {exit_code}). "
                "Check console output above for error details. "
                "Common issues: missing dependencies, database errors, or Ollama connection problems."
            )

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

        # Get WebUI port from environment
        webui_port = int(os.environ.get("OPENWEBUI_PORT", "3000"))

        # Open browser in background
        threading.Thread(
            target=open_browser_delayed, args=(webui_port,), daemon=True
        ).start()

        print("\nServices running!")
        print(f"Access WebUI at: http://localhost:{webui_port}")
        ollama_port = os.environ.get("OLLAMA_PORT", "11434")
        print(f"Ollama API at: http://localhost:{ollama_port}")
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
