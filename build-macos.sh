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

# Download Ollama binary if not present
if [ ! -f "ollama" ]; then
    echo "Downloading Ollama binary..."
    LATEST_TAG=$(curl -s https://api.github.com/repos/ollama/ollama/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    echo "Latest version: $LATEST_TAG"
    # Prefer arch-specific darwin builds; fall back to generic darwin/macos naming
    DOWNLOAD_URL=""
    for p in "darwin.*arm64" "darwin.*amd64" "darwin" "macos"; do
        DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/ollama/ollama/releases/latest" \
            | grep '"browser_download_url"' \
            | sed -E 's/.*"([^"]+)".*/\1/' \
            | grep -iE "$p" || true)
        if [ -n "$DOWNLOAD_URL" ]; then
            DOWNLOAD_URL=$(echo "$DOWNLOAD_URL" | head -n 1)
            break
        fi
    done

    if [ -z "$DOWNLOAD_URL" ]; then
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/${LATEST_TAG}/ollama-darwin"
    fi

    TMPDIR=$(mktemp -d)
    curl -L "$DOWNLOAD_URL" -o "$TMPDIR/ollama_asset"
    # If the asset appears to be an archive, extract it and try to find the binary
    if file "$TMPDIR/ollama_asset" | grep -qi "zip\|gzip\|tar"; then
        echo "Archive detected; extracting to $TMPDIR"
        mkdir -p "$TMPDIR/ollama_unpack"
        if unzip -l "$TMPDIR/ollama_asset" >/dev/null 2>&1; then
            unzip -o "$TMPDIR/ollama_asset" -d "$TMPDIR/ollama_unpack"
        else
            tar -xf "$TMPDIR/ollama_asset" -C "$TMPDIR/ollama_unpack" || true
        fi
        echo "Contents of $TMPDIR/ollama_unpack:"
        ls -la "$TMPDIR/ollama_unpack" || true
        find "$TMPDIR/ollama_unpack" -type f -iname '*ollama*' -print -exec cp {} ollama \; -quit || true
    else
        mv "$TMPDIR/ollama_asset" ollama
    fi
    # Cleanup
    rm -rf "$TMPDIR" || true
    chmod +x ollama
    echo "✓ Ollama downloaded"
else
    echo "✓ Ollama binary already exists"
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
    echo "Listing Contents/Resources inside app bundle for debug:"
    ls -la "dist/OpenWebUI-Ollama.app/Contents/Resources" || true
else
    echo "ERROR: Build failed"
    exit 1
fi
