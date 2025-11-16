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

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
pip3 install pyinstaller

# Download Ollama binary if not present
if [ ! -f "ollama" ]; then
    echo "Downloading Ollama binary..."
    LATEST_TAG=$(curl -s https://api.github.com/repos/ollama/ollama/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    echo "Latest version: $LATEST_TAG"
    URL="https://github.com/ollama/ollama/releases/download/${LATEST_TAG}/ollama-darwin"
    curl -L "$URL" -o ollama
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
else
    echo "ERROR: Build failed"
    exit 1
fi
