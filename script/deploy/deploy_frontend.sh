#!/usr/bin/env bash
set -euo pipefail

# Frontend-only deployment script for LangWeave.
# Builds the main Vue SPA and admin frontend, then rsyncs static files
# to the remote server (backend untouched).
#
# Usage:
#   bash script/deploy/deploy_frontend.sh
#
# Options:
#   --skip-admin     skip building the admin panel
#   --skip-install   skip npm install (use existing node_modules)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"
FRONTEND_DIR="$ROOT_DIR/frontends/fe"
ADMIN_DIR="$ROOT_DIR/frontends/admin"
REMOTE_HOST="root@124.223.72.223"
REMOTE_CURRENT_DIR="/home/biu/chat/current"

SKIP_ADMIN=false
SKIP_INSTALL=false
for arg in "$@"; do
  case "$arg" in
    --skip-admin) SKIP_ADMIN=true ;;
    --skip-install) SKIP_INSTALL=true ;;
  esac
done

echo "============================================"
echo "  LangWeave Frontend Deploy Script"
echo "============================================"

# ---- 1. Clean build dir ----
echo ""
echo "[1/5] Cleaning build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$RELEASE_DIR/frontend"

# ---- 2. Build main frontend ----
echo ""
echo "[2/5] Building main frontend (chat.mybfs.cn)..."
cd "$FRONTEND_DIR"

if [ "$SKIP_INSTALL" = false ] && [ ! -d "node_modules" ]; then
  echo "  --> Running npm install..."
  npm install
fi

npm run build
echo "  --> Output: $FRONTEND_DIR/dist"
cp -r "$FRONTEND_DIR/dist/" "$RELEASE_DIR/frontend/"
echo "  --> Copied to release dir"

# ---- 3. Build admin frontend (optional) ----
if [ "$SKIP_ADMIN" = false ]; then
  echo ""
  echo "[3/5] Building admin frontend (admin.meet.mybfs.cn)..."
  cd "$ADMIN_DIR"

  if [ "$SKIP_INSTALL" = false ] && [ ! -d "node_modules" ]; then
    echo "  --> Running npm install..."
    npm install
  fi

  npm run build
  echo "  --> Output: $ADMIN_DIR/dist"

  mkdir -p "$RELEASE_DIR/admin"
  cp -r "$ADMIN_DIR/dist/" "$RELEASE_DIR/admin/"
  echo "  --> Copied to release dir"
else
  echo ""
  echo "[3/5] Skipping admin build (--skip-admin)"
fi

# ---- 4. Rsync to remote ----
echo ""
echo "[4/5] Rsyncing to remote server..."

rsync -az --delete "$RELEASE_DIR/frontend/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/frontend/"
echo "  --> Main frontend synced"

if [ "$SKIP_ADMIN" = false ]; then
  rsync -az --delete "$RELEASE_DIR/admin/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/admin/"
  echo "  --> Admin frontend synced"
fi

# ---- 5. Reload nginx ----
echo ""
echo "[5/5] Reloading nginx..."
ssh "$REMOTE_HOST" '
  if nginx -t 2>/dev/null; then
    nginx -s reload
    echo "  --> nginx reloaded successfully"
  else
    echo "  --> nginx config test failed, not reloading"
    exit 1
  fi
'

# ---- Done ----
echo ""
echo "============================================"
echo "  Deploy Complete"
echo "============================================"
echo ""
echo "  Main frontend: https://chat.mybfs.cn/"
if [ "$SKIP_ADMIN" = false ]; then
  echo "  Admin frontend: https://admin.meet.mybfs.cn/"
fi
echo "  Remote path:   $REMOTE_CURRENT_DIR/frontend/"
echo ""

# Cleanup
cd "$ROOT_DIR"
rm -rf "$BUILD_DIR"
