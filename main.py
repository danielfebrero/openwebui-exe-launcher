import os
import sys
import subprocess
import webbrowser
import threading
import time
import requests


def get_bundled_path(filename):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def run_ollama():
    app_dir = os.path.dirname(
        os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    )
    ollama_dir = os.path.join(app_dir, ".ollama")
    models_dir = os.path.join(ollama_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    os.environ["OLLAMA_MODELS"] = models_dir
    # GPU Auto-Rift: Native detection; debug if craved
    os.environ["OLLAMA_DEBUG"] = (
        "1"  # Uncomment for GPU/CPU logs (e.g., "ggml_cuda_init: found 1 CUDA devices")
    )
    ollama_exe = get_bundled_path("ollama.exe")
    cmd = [ollama_exe, "serve"]
    p = subprocess.Popen(cmd, cwd=ollama_dir, env=os.environ)
    # Vitality Poll: 11434 API
    for _ in range(60):
        try:
            requests.get("http://localhost:11434/api/tags", timeout=1)
            break  # GPU/CPU allegiance sealed
        except:
            time.sleep(1)
    else:
        raise RuntimeError("Ollama ignition falters")
    return p


def run_webui(ollama_proc):
    app_dir = os.path.dirname(
        os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    )
    data_dir = os.path.join(app_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    os.environ["DATA_DIR"] = data_dir
    os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"
    cmd = [
        sys.executable,
        "-m",
        "open_webui",
        "serve",
        "--port",
        "3000",
        "--host",
        "0.0.0.0",
    ]
    p = subprocess.Popen(cmd, env=os.environ)
    return p


if __name__ == "__main__":
    ollama_p = run_ollama()
    webui_p = run_webui(ollama_p)

    def rift_browser():
        time.sleep(5)
        webbrowser.open("http://localhost:3000")

    threading.Thread(target=rift_browser, daemon=True).start()
    try:
        webui_p.wait()
    finally:
        ollama_p.terminate()
        ollama_p.wait()
