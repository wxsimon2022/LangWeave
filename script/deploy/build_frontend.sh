#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  前端构建 — 构建 fe + admin，输出到 build/release/
# ============================================================
# 用法:
#   bash script/deploy/build_frontend.sh
#   bash script/deploy/build_frontend.sh --skip-admin
#   bash script/deploy/build_frontend.sh --skip-install
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"
FRONTEND_DIR="$ROOT_DIR/frontends/fe"
ADMIN_DIR="$ROOT_DIR/frontends/admin"

SKIP_ADMIN=false
SKIP_INSTALL=false
for arg in "$@"; do
  case "$arg" in
    --skip-admin) SKIP_ADMIN=true ;;
    --skip-install) SKIP_INSTALL=true ;;
  esac
done

mkdir -p "$RELEASE_DIR/frontend"

# ---- 主前端 ----
echo "[build_frontend] 构建主前端 (chat.mybfs.cn)..."
cd "$FRONTEND_DIR"
if [ "$SKIP_INSTALL" = false ] && [ ! -d "node_modules" ]; then
  echo "  → npm install"
  npm install
fi
npm run build
cp -r "$FRONTEND_DIR/dist/" "$RELEASE_DIR/frontend/"
echo "[build_frontend] 主前端完成 → $RELEASE_DIR/frontend/"

# ---- 管理后台 ----
if [ "$SKIP_ADMIN" = false ]; then
  echo "[build_frontend] 构建管理后台 (admin.meet.mybfs.cn)..."
  cd "$ADMIN_DIR"
  if [ "$SKIP_INSTALL" = false ] && [ ! -d "node_modules" ]; then
    echo "  → npm install"
    npm install
  fi
  npm run build
  mkdir -p "$RELEASE_DIR/admin"
  cp -r "$ADMIN_DIR/dist/" "$RELEASE_DIR/admin/"
  echo "[build_frontend] 管理后台完成 → $RELEASE_DIR/admin/"
else
  echo "[build_frontend] 跳过管理后台 (--skip-admin)"
fi

echo "[build_frontend] 完成"
