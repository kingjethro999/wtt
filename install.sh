#!/usr/bin/env bash
set -e

echo "🚀 Installing wtt (Web To Text / Web To HTML CLI)..."

INSTALL_DIR="$HOME/.wtt"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "🔄 Updating existing wtt repository..."
    git -C "$INSTALL_DIR" pull origin main
else
    echo "📦 Cloning wtt repository..."
    git clone https://github.com/kingjethro999/wtt.git "$INSTALL_DIR"
fi

echo "🐍 Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "🎭 Installing Playwright Chromium browser..."
"$INSTALL_DIR/.venv/bin/playwright" install chromium

echo "🔗 Linking binary to $BIN_DIR/wtt..."
chmod +x "$INSTALL_DIR/wtt" "$INSTALL_DIR/wtt.py"
ln -sf "$INSTALL_DIR/wtt" "$BIN_DIR/wtt"

echo "✅ wtt installation complete!"
echo "Run 'wtt --help' to get started."
