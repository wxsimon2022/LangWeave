#!/usr/bin/env bash
# build_local.sh — Build desktop clients locally
#
# Run this on your local development machine (macOS).
# Uses Chinese npm mirrors for faster downloads.
#
# Usage:
#   bash frontends/desktop/build_local.sh [--upload]
#
# Options:
#   --upload    Also publish to GitHub Release after building

set -euo pipefail

cd "$(dirname "$0")"

echo "=== LangWeave Desktop Local Build ==="

# 国内镜像
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
export ELECTRON_BUILDER_BINARIES_MIRROR="${ELECTRON_BUILDER_BINARIES_MIRROR:-https://npmmirror.com/mirrors/electron-builder-binaries/}"

# 安装依赖
if [ ! -d "node_modules" ]; then
  echo ""
  echo "Installing dependencies..."
  npm install
fi

echo ""
echo "Building for macOS (dmg)..."
npx electron-builder --mac --publish=never

echo ""
echo "Building for Windows (exe) — requires wine..."
npx electron-builder --win --publish=never 2>&1 || echo "Windows build skipped (wine may be missing)"

echo ""
echo "Output files:"
ls -lh release/

# 发布到 GitHub Release
if [[ "${1:-}" == "--upload" ]]; then
  echo ""
  echo "Publishing to GitHub Release..."
  ROOT_DIR="$(git rev-parse --show-toplevel)"
  bash "$ROOT_DIR/script/deploy/publish_release.sh"
fi

echo ""
echo "=== Done ==="
