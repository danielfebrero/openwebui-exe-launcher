#!/usr/bin/env bash
set -euo pipefail

LATEST_TAG="$(curl -s https://api.github.com/repos/ollama/ollama/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')"
echo "Downloading Ollama $LATEST_TAG"

# print assets
curl -s "https://api.github.com/repos/ollama/ollama/releases/latest" | grep '"name"' | sed -E 's/.*"([^"]+)".*/\1/' | sed 's/^/ - /' || true

PATTERNS=("darwin.*arm64" "darwin.*amd64" "darwin" "macos")
DOWNLOAD_URL=""
for p in "${PATTERNS[@]}"; do
  echo "Searching assets matching: $p"
  DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/ollama/ollama/releases/latest" \
    | grep '"browser_download_url"' \
    | sed -E 's/.*"([^"]+)".*/\1/' \
    | grep -iE "$p" \
    | grep -viE 'rocm|cuda|hip|ggml|lib' \
    | head -n 1 || true)
  if [ -n "$DOWNLOAD_URL" ]; then
    echo "Selected: $DOWNLOAD_URL"
    break
  fi
done

if [ -z "$DOWNLOAD_URL" ]; then
  echo "No darwin asset found in release; falling back to 'ollama-darwin'"
  DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/${LATEST_TAG}/ollama-darwin"
fi

TEMP_DIR="$(mktemp -d)"
OLLAMA_DEBUG_DIR="$(pwd)/ollama_artifacts"
mkdir -p "$OLLAMA_DEBUG_DIR"

for i in 1 2 3; do
  echo "Download attempt $i/3..."
  if curl -L "$DOWNLOAD_URL" -o "$TEMP_DIR/ollama_asset"; then
    file "$TEMP_DIR/ollama_asset" || true
    if file "$TEMP_DIR/ollama_asset" | grep -qi "zip\|gzip\|tar"; then
      echo "Archive downloaded; extracting to temp for scan"
      mkdir -p "$TEMP_DIR/ollama_unpack"
      if unzip -l "$TEMP_DIR/ollama_asset" >/dev/null 2>&1; then
        unzip -o "$TEMP_DIR/ollama_asset" -d "$TEMP_DIR/ollama_unpack"
      else
        tar -xf "$TEMP_DIR/ollama_asset" -C "$TEMP_DIR/ollama_unpack" || true
      fi
      echo "Contents of $TEMP_DIR/ollama_unpack:"
      ls -la "$TEMP_DIR/ollama_unpack" || true
      find "$TEMP_DIR/ollama_unpack" -type f -iname '*ollama*' -print -exec cp {} "$OLLAMA_DEBUG_DIR/" \; -quit || true
    else
      mv "$TEMP_DIR/ollama_asset" "$OLLAMA_DEBUG_DIR/ollama"
    fi

    if [ -f "$OLLAMA_DEBUG_DIR/ollama" ] && [ -s "$OLLAMA_DEBUG_DIR/ollama" ]; then
      chmod +x "$OLLAMA_DEBUG_DIR/ollama" || true
      cp "$OLLAMA_DEBUG_DIR/ollama" ollama || true
      echo "✓ ollama binary prepared"
      break
    fi
  fi

  if [ $i -eq 3 ]; then
    echo "ERROR: ollama download failed after 3 attempts"
    exit 1
  fi

  echo "Retrying in 5 seconds..."
  sleep 5
done

# leave debug files in ./ollama_artifacts to be picked up by artifact upload
rm -rf "$TEMP_DIR" || true

exit 0
