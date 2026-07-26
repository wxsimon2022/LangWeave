#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  打包 — 将后端 + 前端 + SSL + 桌面端 组装为完整发布包
# ============================================================
# 用法:
#   bash script/deploy/package.sh
#
# 前置条件: 先运行 build_backend.sh + build_frontend.sh
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"
DESKTOP_DIR="$ROOT_DIR/frontends/desktop"

if [ ! -d "$RELEASE_DIR" ]; then
  echo "[package] 错误: 未找到 $RELEASE_DIR"
  echo "  请先运行 build_backend.sh 和 build_frontend.sh"
  exit 1
fi

echo "[package] 组装发布包..."

# ---- SSL 证书 ----
echo "  → SSL 证书"
SSL_SRC="$ROOT_DIR/script/chat.mybfs.cn_nginx"
if [ -d "$SSL_SRC" ]; then
  mkdir -p "$RELEASE_DIR/ssl"
  cp "$SSL_SRC/chat.mybfs.cn.key"        "$RELEASE_DIR/ssl/" 2>/dev/null || true
  cp "$SSL_SRC/chat.mybfs.cn_bundle.pem" "$RELEASE_DIR/ssl/" 2>/dev/null || true
  cp "$SSL_SRC/chat.mybfs.cn_bundle.crt" "$RELEASE_DIR/ssl/" 2>/dev/null || true
  echo "    $RELEASE_DIR/ssl/"
fi

# ---- 桌面端 ----
echo "  → 桌面端安装包"
if [ -d "$DESKTOP_DIR/release" ]; then
  mkdir -p "$RELEASE_DIR/frontend/desktop"
  find "$DESKTOP_DIR/release" -maxdepth 2 \( -name "*.dmg" -o -name "*.exe" -o -name "*.AppImage" \) \
    -exec cp {} "$RELEASE_DIR/frontend/desktop/" \;
  echo "    $RELEASE_DIR/frontend/desktop/"
fi

# ---- 统计 ----
echo ""
echo "[package] 发布包内容:"
echo "  后端:    $(find "$RELEASE_DIR" -maxdepth 1 -name '*.py' -o -name 'pyproject.toml' -o -name 'requirements.txt' | wc -l) 个文件"
echo "  主前端:  $(ls "$RELEASE_DIR/frontend/" 2>/dev/null | wc -l) 个文件"
echo "  管理后台: $(ls "$RELEASE_DIR/admin/" 2>/dev/null | wc -l) 个文件"
echo "  SSL:     $(ls "$RELEASE_DIR/ssl/" 2>/dev/null | wc -l) 个文件"
echo "  桌面端:  $(ls "$RELEASE_DIR/frontend/desktop/" 2>/dev/null | wc -l) 个文件"
echo ""
echo "[package] 完成 → $RELEASE_DIR"
du -sh "$RELEASE_DIR"
