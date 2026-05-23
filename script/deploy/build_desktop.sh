#!/usr/bin/env bash
set -euo pipefail

# Desktop-only build script.
# Builds the Electron desktop client (macOS + Windows) and copies artifacts
# into the proper release directory for uploading and serving.
#
# Usage:
#   bash script/deploy/build_desktop.sh
#
# Output:
#   - Build artifacts in frontends/desktop/release/
#   - Copies .dmg / .exe / .AppImage to script/deploy/build/release/frontend/desktop/
#
# Environment:
#   CI_SKIP_DESKTOP  — set to any value to skip the build
#   DESKTOP_VERSION  — explicit version string (e.g. "1.0.25"); if unset,
#                      reads from ROOT_DIR's DEPLOY_VERSION file (written by deploy_all.sh)
#                      or falls back to package.json version

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESKTOP_DIR="$ROOT_DIR/frontends/desktop"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"

if [[ -n "${CI_SKIP_DESKTOP:-}" ]]; then
  echo "CI_SKIP_DESKTOP is set, skipping desktop build."
  exit 0
fi

echo "[desktop] Building desktop client (macOS + Windows)"

cd "$DESKTOP_DIR"

# --- Sync package.json version ---
DESKTOP_VERSION="${DESKTOP_VERSION:-}"
if [[ -z "$DESKTOP_VERSION" && -f "$ROOT_DIR/.deploy-version" ]]; then
  DESKTOP_VERSION="$(cat "$ROOT_DIR/.deploy-version" | tr -d '[:space:]' | sed 's/^v//')"
fi
if [[ -n "$DESKTOP_VERSION" ]]; then
  echo "[desktop] Setting package.json version to $DESKTOP_VERSION"
  # Use node to safely update package.json
  node -e "
    const pkg = require('$DESKTOP_DIR/package.json');
    pkg.version = '$DESKTOP_VERSION';
    require('fs').writeFileSync('$DESKTOP_DIR/package.json', JSON.stringify(pkg, null, 2) + '\n');
  "
fi

# 使用国内镜像加速 Electron 下载
export ELECTRON_MIRROR="${ELECTRON_MIRROR:-https://npmmirror.com/mirrors/electron/}"
export ELECTRON_BUILDER_BINARIES_MIRROR="${ELECTRON_BUILDER_BINARIES_MIRROR:-https://npmmirror.com/mirrors/electron-builder-binaries/}"

if [ ! -d "node_modules" ]; then
  npm install 2>&1 || true
fi

# Build macOS (dmg) and Windows (exe)
npx electron-builder --mac --win --publish=never 2>&1 || {
  echo "[desktop] Build failed (see above for details)"
  exit 1
}

echo "[desktop] Build complete. Artifacts in: $DESKTOP_DIR/release/"

# Copy artifacts into release bundle for deployment
echo "[desktop] Copying artifacts to release bundle..."
mkdir -p "$RELEASE_DIR/frontend/desktop"
if [ -d "$DESKTOP_DIR/release" ]; then
  find "$DESKTOP_DIR/release" -maxdepth 2 \( -name "*.dmg" -o -name "*.exe" -o -name "*.AppImage" \) \
    -exec cp {} "$RELEASE_DIR/frontend/desktop/" \;
  echo "[desktop] Copied artifacts:"
  ls -lh "$RELEASE_DIR/frontend/desktop/" 2>/dev/null || true
fi

# --- Restore package.json to prevent dirty git state ---
node -e "
  const pkg = require('$DESKTOP_DIR/package.json');
  pkg.version = '1.0.0';
  require('fs').writeFileSync('$DESKTOP_DIR/package.json', JSON.stringify(pkg, null, 2) + '\n');
"

echo "[desktop] Done."
