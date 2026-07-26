#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  LangWeave 一键部署脚本
#  构建后端 + 前端 → 打包 → 推送远程 → 更新 nginx → 发版
# ============================================================
# 用法:
#   bash script/deploy/deploy.sh                         # 完整发布
#   bash script/deploy/deploy.sh v1.2.3                   # 指定版本号
#   bash script/deploy/deploy.sh --skip-frontend          # 只构建后端
#   bash script/deploy/deploy.sh --skip-desktop           # 跳过桌面端
#   bash script/deploy/deploy.sh --skip-github            # 跳过 GitHub Release
#   bash script/deploy/deploy.sh --skip-all-build         # 仅推送已有包
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

SKIP_FRONTEND=false
SKIP_DESKTOP=false
SKIP_GITHUB=false
SKIP_ALL_BUILD=false
EXPLICIT_TAG=""
for arg in "$@"; do
  case "$arg" in
    --skip-frontend)  SKIP_FRONTEND=true ;;
    --skip-desktop)   SKIP_DESKTOP=true ;;
    --skip-github)    SKIP_GITHUB=true ;;
    --skip-all-build) SKIP_ALL_BUILD=true ;;
    v*)               EXPLICIT_TAG="$arg" ;;
  esac
done

echo "============================================"
echo "  LangWeave 一键部署"
echo "============================================"
echo ""

# ══════════════════════════════════════════════════
# 1. 构建后端
# ══════════════════════════════════════════════════
if [ "$SKIP_ALL_BUILD" = false ]; then
echo "[deploy] [1/6] 构建后端..."
cd "$ROOT_DIR"

rm -rf "$BUILD_DIR"
  mkdir -p "$RELEASE_DIR"

  rsync -a \
    --exclude ".git" \
    --exclude ".idea" \
    --exclude ".pytest_cache" \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude "frontends" \
    --exclude "script/deploy/build" \
    --exclude ".env" \
    --exclude ".env.prod" \
    app langweave main.py pyproject.toml requirements.txt README.md .env.example \
    "$RELEASE_DIR/"

  if [ -f "$ROOT_DIR/.env.prod" ]; then
    cp "$ROOT_DIR/.env.prod" "$RELEASE_DIR/.env"
    echo "  → 已复制 .env.prod → .env"
  else
    echo "  → 警告: 未找到 .env.prod，跳过"
  fi
  echo "  ✅ 后端构建完成"

  # ══════════════════════════════════════════════════
  # 2. 构建前端
  # ══════════════════════════════════════════════════
  if [ "$SKIP_FRONTEND" = false ]; then
    echo ""
    echo "[deploy] [2/6] 构建前端..."

    # 主前端 (fe)
    echo "  → 主前端 (chat.mybfs.cn)..."
    cd "$ROOT_DIR/frontends/fe"
    if [ ! -d "node_modules" ]; then
      npm install
    fi
    npm run build
    mkdir -p "$RELEASE_DIR/frontend"
    cp -r dist/* "$RELEASE_DIR/frontend/"
    echo "    ✅ 主前端完成"

    # 管理后台 (admin)
    echo "  → 管理后台 (admin.meet.mybfs.cn)..."
    cd "$ROOT_DIR/frontends/admin"
    if [ ! -d "node_modules" ]; then
      npm install
    fi
    npm run build
    mkdir -p "$RELEASE_DIR/admin"
    cp -r dist/* "$RELEASE_DIR/admin/"
    echo "    ✅ 管理后台完成"
  else
    echo ""
    echo "[deploy] [2/6] 跳过前端构建 (--skip-frontend)"
  fi

  # ══════════════════════════════════════════════════
  # 3. 打包 (SSL + 桌面端)
  # ══════════════════════════════════════════════════
  echo ""
  echo "[deploy] [3/6] 打包..."

  # SSL 证书
  SSL_SRC="$ROOT_DIR/script/chat.mybfs.cn_nginx"
  if [ -d "$SSL_SRC" ]; then
    mkdir -p "$RELEASE_DIR/ssl"
    cp "$SSL_SRC/chat.mybfs.cn.key"        "$RELEASE_DIR/ssl/" 2>/dev/null || true
    cp "$SSL_SRC/chat.mybfs.cn_bundle.pem" "$RELEASE_DIR/ssl/" 2>/dev/null || true
    cp "$SSL_SRC/chat.mybfs.cn_bundle.crt" "$RELEASE_DIR/ssl/" 2>/dev/null || true
    echo "  → SSL 证书: $RELEASE_DIR/ssl/"
  fi

  # 桌面端
  if [ "$SKIP_DESKTOP" = false ] && [ -f "$ROOT_DIR/script/deploy/build_desktop.sh" ]; then
    echo "  → 桌面端..."
    bash "$ROOT_DIR/script/deploy/build_desktop.sh" 2>&1 || echo "    ⚠ 桌面端构建失败 (继续)..."
  fi

  echo "  ✅ 打包完成"
else
  echo "[deploy] 跳过构建阶段 (--skip-all-build)"
fi

# ══════════════════════════════════════════════════
# 4. Rsync 发布包到远程
# ══════════════════════════════════════════════════
echo ""
echo "[deploy] [4/6] Rsync 发布包到远程..."
ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_SHARED_DIR' '$REMOTE_CURRENT_DIR'"
rsync -az --delete "$RELEASE_DIR/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/"
echo "  ✅ 发布包已推送"

# ══════════════════════════════════════════════════
# 5. Rsync Nginx 配置 + 远程部署
# ══════════════════════════════════════════════════
echo ""
echo "[deploy] [5/6] Rsync Nginx 配置..."
rsync -az "$ROOT_DIR/script/deploy/nginx.chat.mybfs.cn.conf" \
  "$REMOTE_HOST:$REMOTE_NGINX_DIR/chat.mybfs.cn.conf"
rsync -az "$ROOT_DIR/script/deploy/nginx.admin.meet.mybfs.cn.conf" \
  "$REMOTE_HOST:$REMOTE_NGINX_DIR/admin.meet.mybfs.cn.conf"
echo "  ✅ Nginx 配置已推送"

echo ""
echo "[deploy] 远程环境部署..."
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
    if ! ss -tln "sport = :3002" 2>/dev/null | grep -q .; then
      sleep 1
      break
    fi
    sleep 1
  done
  if ss -tln "sport = :3002" 2>/dev/null | grep -q .; then
    echo "  → 端口仍被占用，强制释放..."
    fuser -k 3002/tcp 2>/dev/null || true
    sleep 2
  fi
cd "$REMOTE_CURRENT_DIR"
touch app.log
setsid "$REMOTE_VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 3002 > app.log 2>&1 < /dev/null &
sleep 3

if ! ss -tln "sport = :3002" 2>/dev/null | grep -q .; then
  echo "  ⚠ Uvicorn 启动失败，查看日志:"
  tail -n 30 app.log || true
  exit 1
fi

echo "  → 重载 Nginx"
nginx -t && nginx -s reload
echo "  ✅ 远程部署完成"
'
echo "  ✅ 远程部署完成"

# ══════════════════════════════════════════════════
# 6. Git tag + push + GitHub Release
# ══════════════════════════════════════════════════
echo ""
echo "[deploy] [6/6] Git 打标签并推送..."
cd "$ROOT_DIR"

# 计算下一个 tag
TAG="$EXPLICIT_TAG"
if [ -z "$TAG" ]; then
  LATEST_TAG="$(git tag --sort=-v:refname 2>/dev/null | head -1)"
  if [[ -n "$LATEST_TAG" && "$LATEST_TAG" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    TAG="v${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.$((BASH_REMATCH[3] + 1))"
  else
    TAG="v1.0.1"
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

# GitHub Release
if [ "$SKIP_GITHUB" = false ] && command -v gh &>/dev/null; then
  echo ""
  echo "  → 创建 GitHub Release $TAG..."

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

# ══════════════════════════════════════════════════
# 完成
# ══════════════════════════════════════════════════
echo ""
echo "============================================"
echo "  ✅ 发版完成: $TAG"
echo "============================================"
echo ""
echo "  Web:   https://chat.mybfs.cn/"
echo "  Admin: https://admin.meet.mybfs.cn/"
echo "  Tag:   $TAG"
echo ""
