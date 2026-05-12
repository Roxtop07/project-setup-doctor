#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
EXTENSION_DIR="$PROJECT_DIR/extension"

PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$PLATFORM" in
    darwin)  PLATFORM="darwin" ;;
    linux)   PLATFORM="linux" ;;
    mingw*|msys*|cygwin*) PLATFORM="win32" ;;
    *)       echo "Unsupported platform: $PLATFORM"; exit 1 ;;
esac

case "$ARCH" in
    arm64|aarch64) ARCH="arm64" ;;
    x86_64|amd64)  ARCH="x64" ;;
    *)             echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

TARGET="${1:-$PLATFORM-$ARCH}"
BIN_DIR="$EXTENSION_DIR/bin/$TARGET"

echo "Building securecode-backend for $TARGET..."

cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt pyinstaller>=6.0.0

echo "Running PyInstaller (onedir mode)..."
pyinstaller securecode-backend.spec --clean --noconfirm --distpath "$BACKEND_DIR/dist" 2>&1

rm -rf "$BIN_DIR"
mkdir -p "$(dirname "$BIN_DIR")"
mv "$BACKEND_DIR/dist/securecode-backend" "$BIN_DIR"

if [ "$PLATFORM" != "win32" ]; then
    chmod -R +x "$BIN_DIR"
fi

rm -rf "$BACKEND_DIR/build" "$BACKEND_DIR/dist"

SIZE=$(du -sh "$BIN_DIR" | cut -f1)
echo ""
echo "Build complete: $BIN_DIR/ ($SIZE)"
echo "Binary: $BIN_DIR/securecode-backend"
