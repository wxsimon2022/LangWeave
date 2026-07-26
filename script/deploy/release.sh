#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  发版 — 推送发布包到远程服务器 + Git 打标签 + GitHub Release
# ============================================================
# 用法:
#   bash script/deploy/release.sh               # 自动递增 tag
#   bash script/deploy/release.sh v1.2.3         # 使用指定 tag
#   bash script/deploy/release.sh --skip-github  # 跳过 GitHub Release
#   bash script/deploy/release.sh --skip-desktop # 跳过桌面端构建
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"

REMOTE_HOST="root@124.223.72.223"
REMOTE_APP_DIR="/home/biu/chat"
REMOTE_CURRENT_DIR="$REMOTE_APP_DIR/current"
REMOTE_SHARED_DIR="$REMOTE_APP_DIR/shared"
REMOTE_ENV_FILE="$REMOTE_APP_DIR/shared/.env"
REMOTE_VENV_DIR="$REMOTE_SHARED_DIR/.venv"
REMOTE_PYTHON_BIN="$REMOTE_SHARED_DIR/python-bin"
REMOTE_NGINX_DIR="/etc/nginx/conf.d"

SKIP_GITHUB=false
SKIP_DESKTOP=false
EXPLICIT_TAG=""
for arg in "$@"; do
  case "$arg" in
    --skip-github) SKIP_GITHUB=true ;;
    --skip-desktop) SKIP_DESKTOP=true ;;
    v*) EXPLICIT_TAG="$arg" ;;
  esac
done

# ──────────────────────────────────────────────
# 0. 检查发布包
# ──────────────────────────────────────────────
if [ ! -d "$RELEASE_DIR" ]; then
  echo "[release] 错误: 未找到 $RELEASE_DIR"
  echo "  请先依次运行:"
  echo "    bash script/deploy/build_backend.sh"
  echo "    bash script/deploy/build_frontend.sh"
  echo "    bash script/deploy/package.sh"
  exit 1
fi

# ──────────────────────────────────────────────
# 1. Rsync 发布包到远程
# ──────────────────────────────────────────────
echo "[release] [1/5] Rsync 发布包到远程..."
ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_SHARED_DIR' '$REMOTE_CURRENT_DIR'"
rsync -az --delete "$RELEASE_DIR/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/"

# ──────────────────────────────────────────────
# 2. Rsync Nginx 配置
# ──────────────────────────────────────────────
echo "[release] [2/5] Rsync Nginx 配置..."
rsync -az "$ROOT_DIR/script/deploy/nginx.chat.mybfs.cn.conf" \
  "$REMOTE_HOST:$REMOTE_NGINX_DIR/chat.mybfs.cn.conf"
rsync -az "$ROOT_DIR/script/deploy/nginx.admin.meet.mybfs.cn.conf" \
  "$REMOTE_HOST:$REMOTE_NGINX_DIR/admin.meet.mybfs.cn.conf"

# ──────────────────────────────────────────────
# 3. 远程部署
# ──────────────────────────────────────────────
echo "[release] [3/5] 远程环境部署..."
ssh "$REMOTE_HOST" '
set -euo pipefail

REMOTE_APP_DIR="/home/biu/chat"
REMOTE_CURRENT_DIR="$REMOTE_APP_DIR/current"
REMOTE_SHARED_DIR="$REMOTE_APP_DIR/shared"
REMOTE_ENV_FILE="$REMOTE_APP_DIR/shared/.env"
REMOTE_VENV_DIR="$REMOTE_SHARED_DIR/.venv"
REMOTE_PYTHON_BIN="$REMOTE_SHARED_DIR/python-bin"

# 同步 .env 到 shared 目录并建立链接
if [ -f "$REMOTE_CURRENT_DIR/.env" ]; then
  cp "$REMOTE_CURRENT_DIR/.env" "$REMOTE_ENV_FILE"
  ln -sfn "$REMOTE_ENV_FILE" "$REMOTE_CURRENT_DIR/.env"
fi

echo "  → Python 环境"
if command -v python3.11 &>/dev/null; then
  echo "python3.11" > "$REMOTE_PYTHON_BIN"
fi
PYTHON_CMD="$(cat "$REMOTE_PYTHON_BIN")"
$PYTHON_CMD --version

# 检查是否需要重建虚拟环境
if [ -x "$REMOTE_VENV_DIR/bin/python" ]; then
  VENV_PY_VERSION="$($REMOTE_VENV_DIR/bin/python -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")")"
  TARGET_PY_VERSION="$($PYTHON_CMD -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")")"
  if [ "$VENV_PY_VERSION" != "$TARGET_PY_VERSION" ]; then
    echo "  → Python 版本变更 $VENV_PY_VERSION → $TARGET_PY_VERSION，重建虚拟环境"
    rm -rf "$REMOTE_VENV_DIR"
  fi
fi

if [ ! -d "$REMOTE_VENV_DIR" ]; then
  $PYTHON_CMD -m venv "$REMOTE_VENV_DIR"
fi

"$REMOTE_VENV_DIR/bin/pip" install --upgrade pip -q
"$REMOTE_VENV_DIR/bin/pip" install -r "$REMOTE_CURRENT_DIR/requirements.txt" -q

echo "  → 启动 Uvicorn"
  pkill -f "\[u\]vicorn main:app" || true
  echo "  → 等待进程退出..."
  for i in $(seq 1 8); do
    if ! ss -tln "sport = :8000" 2>/dev/null | grep -q .; then
      sleep 1
      break
    fi
    sleep 1
  done
  # 如果进程还在，直接杀端口
  if ss -tln "sport = :8000" 2>/dev/null | grep -q .; then
    echo "  → 端口仍被占用，强制释放..."
    fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
  fi
cd "$REMOTE_CURRENT_DIR"
touch app.log
setsid "$REMOTE_VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 < /dev/null &
sleep 3

if ! ss -tln "sport = :8000" 2>/dev/null | grep -q .; then
  echo "  ⚠ Uvicorn 启动失败，查看日志:"
  tail -n 30 app.log || true
  exit 1
fi

echo "  → 重载 Nginx"
nginx -t && nginx -s reload
echo "  ✅ 远程部署完成"
'

# ──────────────────────────────────────────────
# 4. Git tag & push
# ──────────────────────────────────────────────
echo "[release] [4/5] Git 打标签并推送..."
cd "$ROOT_DIR"

# 计算下一个 tag
TAG="$EXPLICIT_TAG"
if [ -z "$TAG" ]; then
  TAG="v1.0.1"
  LATEST_TAG="$(git tag --sort=-v:refname 2>/dev/null | head -1)"
  if [[ -n "$LATEST_TAG" && "$LATEST_TAG" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    TAG="v${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.$((BASH_REMATCH[3] + 1))"
  fi
fi

if git status --porcelain 2>/dev/null | grep -q .; then
  echo "  → 提交本地改动..."
  git add -A
  git commit -m "chore: auto-commit before deploy $TAG"
fi

echo "  → 打标签 $TAG"
git tag "$TAG"
git push origin master --tags 2>&1
echo "  ✅ 已推送 $TAG"

# ──────────────────────────────────────────────
# 5. Desktop + GitHub Release
# ──────────────────────────────────────────────
echo "[release] [5/5] GitHub Release..."

# 写出版本号供 build_desktop.sh 使用
echo "${TAG#v}" > "$ROOT_DIR/.deploy-version"

if [ "$SKIP_DESKTOP" = false ] && [ -f "$ROOT_DIR/script/deploy/build_desktop.sh" ]; then
  echo "  → 构建桌面端..."
  bash "$ROOT_DIR/script/deploy/build_desktop.sh" 2>&1 || echo "  ⚠ 桌面端构建失败 (继续)..."
else
  echo "  → 跳过桌面端构建"
fi

# 清理版本文件
rm -f "$ROOT_DIR/.deploy-version"

if [ "$SKIP_GITHUB" = false ] && command -v gh &>/dev/null; then
  echo "  → 创建 GitHub Release $TAG..."

  # 收集桌面端构件
  ASSETS=()
  DESKTOP_RELEASE="$ROOT_DIR/frontends/desktop/release"
  if [ -d "$DESKTOP_RELEASE" ]; then
    while IFS= read -r -d '' f; do
      ASSETS+=("$f")
    done < <(find "$DESKTOP_RELEASE" -maxdepth 2 \( -name "*.dmg" -o -name "*.exe" -o -name "*.AppImage" \) -print0)
  fi

  MAIN_HASH="$(git rev-parse --short HEAD)"
  gh release create "$TAG" \
    --repo "wxsimon2022/LangWeave" \
    --title "LangWeave $TAG" \
    --notes "## LangWeave $TAG

- Web: https://chat.mybfs.cn/
- Commit: \`$MAIN_HASH\`" \
    "${ASSETS[@]}" 2>&1 || echo "  ⚠ GitHub Release 失败 (可手动创建)"

  echo "  ✅ GitHub Release 完成"
elif [ "$SKIP_GITHUB" = false ]; then
  echo "  → 跳过 GitHub Release (gh CLI 未安装)"
  echo "    安装: https://cli.github.com/"
  echo "    手动创建: https://github.com/wxsimon2022/LangWeave/releases/new?tag=$TAG"
fi

# ──────────────────────────────────────────────
# 完成
# ──────────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ 发版完成: $TAG"
echo "============================================"
echo ""
echo "  Web:   https://chat.mybfs.cn/"
echo "  Admin: https://admin.meet.mybfs.cn/"
echo "  Tag:   $TAG"
echo ""
