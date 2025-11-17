#!/bin/bash
# Build script for Open WebUI + Ollama Portable Launcher (macOS)

set -e  # Exit on error

echo "============================================"
echo "Building Open WebUI + Ollama for macOS"
echo "============================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    VERSION_OUTPUT=$(python3 --version 2>&1 || echo "unknown version")
    echo "ERROR: Python 3.11 or newer is required (found ${VERSION_OUTPUT})"
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

# Copy frontend build from installed open-webui package
echo "Copying frontend build from open-webui package..."
python3 -c "
import open_webui
import shutil
import os
frontend_path = os.path.join(os.path.dirname(open_webui.__file__), 'frontend')
if os.path.exists(frontend_path):
    shutil.copytree(frontend_path, 'build', dirs_exist_ok=True)
    print('Frontend copied to build directory')
else:
    print('ERROR: Frontend not found in open-webui package')
    exit(1)
"

# Download Ollama binary if not present (use shared ci script for consistency)
if [ ! -f "ollama" ]; then
    echo "Downloading Ollama binary using ci/download-ollama.sh"
    bash ci/download-ollama.sh
else
    echo " Ollama binary already exists"
fi

# Build the app
echo "Building .app bundle with PyInstaller..."
pyinstaller --clean openwebui-portable-macos.spec

# Check if build succeeded
if [ -d "dist/OpenWebUI-Ollama.app" ]; then
    echo "✓ Build successful!"
    echo ""
    echo "Application: dist/OpenWebUI-Ollama.app"
    echo ""
    echo "To create DMG:"
    echo "  brew install create-dmg"
    echo "  create-dmg --volname 'OpenWebUI-Ollama' \\"
    echo "    --window-size 600 400 \\"
    echo "    --app-drop-link 425 120 \\"
    echo "    OpenWebUI-Ollama.dmg dist/OpenWebUI-Ollama.app"
    echo ""
    echo "To run:"
    echo "  open dist/OpenWebUI-Ollama.app"
    echo "Listing Contents/MacOS inside app bundle for debug:"
    ls -la "dist/OpenWebUI-Ollama.app/Contents/MacOS" || true
    OLLAMA_PATH="dist/OpenWebUI-Ollama.app/Contents/MacOS/ollama"
    OLLAMA_ALT_RESOURCES="dist/OpenWebUI-Ollama.app/Contents/Resources/ollama"
    OLLAMA_ALT_FRAMEWORKS="dist/OpenWebUI-Ollama.app/Contents/Frameworks/ollama"

    if [ -f "$OLLAMA_PATH" ] || [ -L "$OLLAMA_PATH" ]; then
        FOUND_PATH="$OLLAMA_PATH"
    elif [ -f "$OLLAMA_ALT_RESOURCES" ] || [ -L "$OLLAMA_ALT_RESOURCES" ]; then
        FOUND_PATH="$OLLAMA_ALT_RESOURCES"
    elif [ -f "$OLLAMA_ALT_FRAMEWORKS" ] || [ -L "$OLLAMA_ALT_FRAMEWORKS" ]; then
        FOUND_PATH="$OLLAMA_ALT_FRAMEWORKS"
    fi

    if [ -n "$FOUND_PATH" ]; then
        echo "Found bundled ollama binary inside app at: $FOUND_PATH"
        ls -la "$FOUND_PATH" || true
        if [ -L "$FOUND_PATH" ]; then
            echo "ollama is a symlink pointing to: $(readlink "$FOUND_PATH")"
            if [ -f "$(readlink "$FOUND_PATH")" ]; then
                echo "Symlink target exists inside bundle"
            else
                echo "Symlink target is missing or not a file"
            fi
        fi
        file "$FOUND_PATH" || true
    fi
    echo "Listing Contents/Resources inside app bundle for debug:"
    ls -la "dist/OpenWebUI-Ollama.app/Contents/Resources" || true
else
    echo "ERROR: Build failed"
    exit 1
fi
