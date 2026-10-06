#!/bin/bash
# Build desktop clients for all platforms
# Requires: node_modules installed (npm install)
set -e

cd "$(dirname "$0")"

echo "=== Building LangWeave Desktop ==="

# Install deps (skip if already installed)
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

echo ""
echo "1) Building for macOS (x64 + arm64)..."
npx electron-builder --mac --publish=never 2>&1 | tail -5

echo ""
echo "2) Building for Windows (x64)..."
npx electron-builder --win --publish=never 2>&1 | tail -5

echo ""
echo "3) Building for Linux (x64)..."
npx electron-builder --linux --publish=never 2>&1 | tail -5

echo ""
echo "=== All builds complete ==="
echo "Output directory: $(pwd)/release/"
ls -lh release/
