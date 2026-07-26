#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  后端构建 + 部署 — 打包 Python 源码 → rsync 到远程 → 重启
# ============================================================
# 用法:
#   bash script/deploy/build_backend.sh          # 打包 + 部署 + 重启
#   bash script/deploy/build_backend.sh --local  # 仅打包，不推送远程
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"

REMOTE_HOST="root@124.223.72.223"
REMOTE_CURRENT_DIR="/home/biu/chat/current"
REMOTE_SHARED_DIR="/home/biu/chat/shared"
REMOTE_ENV_FILE="$REMOTE_SHARED_DIR/.env"
REMOTE_VENV_DIR="$REMOTE_SHARED_DIR/.venv"
REMOTE_PYTHON_BIN="$REMOTE_SHARED_DIR/python-bin"

LOCAL_ONLY=false
[[ "${1:-}" == "--local" ]] && LOCAL_ONLY=true

# ── 1. 打包 ──
echo "[build_backend] 打包后端源码..."
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

# 生产环境配置：.env.prod → .env（同步到机器上直接可用）
if [ -f "$ROOT_DIR/.env.prod" ]; then
  cp "$ROOT_DIR/.env.prod" "$RELEASE_DIR/.env"
  echo "[build_backend] 已复制 .env.prod → .env"
else
  echo "[build_backend] 警告: 未找到 .env.prod，跳过"
fi

echo "[build_backend] 打包完成 → $RELEASE_DIR"
ls -lh "$RELEASE_DIR" --file-type 2>/dev/null || true

# ── 仅打包模式 ──
if [ "$LOCAL_ONLY" = true ]; then
  exit 0
fi

# ── 2. 部署到远程 ──
echo ""
echo "[build_backend] [1/2] Rsync 到远程..."
ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_SHARED_DIR' '$REMOTE_CURRENT_DIR'"
rsync -az --delete "$RELEASE_DIR/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/"

# ── 3. 远程环境准备 + 重启 ──
echo "[build_backend] [2/2] 远程环境准备 + 重启服务..."
ssh "$REMOTE_HOST" '
set -euo pipefail

REMOTE_CURRENT_DIR="/home/biu/chat/current"
REMOTE_SHARED_DIR="/home/biu/chat/shared"
REMOTE_ENV_FILE="$REMOTE_SHARED_DIR/.env"
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

echo "  → 重启 Uvicorn"
pkill -f "\[u\]vicorn main:app" || true
echo "  → 等待端口 8000 释放..."
for i in $(seq 1 10); do
  if ! ss -tln "sport = :8000" 2>/dev/null | grep -q .; then
    break
  fi
  sleep 1
done
cd "$REMOTE_CURRENT_DIR"
touch app.log
setsid "$REMOTE_VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 < /dev/null &
sleep 3

if ! pgrep -f "\[u\]vicorn main:app" >/dev/null 2>&1; then
  echo "  ⚠ Uvicorn 启动失败，查看日志:"
  tail -n 30 app.log || true
  exit 1
fi

echo "  ✅ 服务已重启"
'

# ── 清理 ──
rm -rf "$BUILD_DIR"
echo ""
echo "[build_backend] ✅ 后端部署完成"
