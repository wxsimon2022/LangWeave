#!/usr/bin/env bash
set -euo pipefail

# Backend-only deployment script — fast deploy for Python code changes.
# Skips frontend build, admin build, desktop build, nginx, git tag, and release.
# Just rsyncs the Python source to the remote, restarts uvicorn.
#
# Usage:
#   bash script/deploy/deploy_backend.sh
#
# Optional: pass a custom commit message
#   bash script/deploy/deploy_backend.sh "fix: adjust heartbeat timeout"

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

echo "[1/4] Preparing backend-only release bundle"
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
mkdir -p "$RELEASE_DIR/config"
cp "$ROOT_DIR/.env.prod" "$RELEASE_DIR/config/.env.prod"

echo "[2/4] Rsync backend code to remote"
rsync -az --delete "$RELEASE_DIR/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/"

echo "[3/4] Running remote restart"
ssh "$REMOTE_HOST" "
set -euo pipefail

# 每次部署都将最新的 .env.prod 同步到 shared/.env
# 确保新增的环境变量（如 LANGWEAVE_REDIS_URL）被正确设置
cp '$REMOTE_CURRENT_DIR/config/.env.prod' '$REMOTE_ENV_FILE' 2>/dev/null || true

cd '$REMOTE_CURRENT_DIR'
ln -sfn '$REMOTE_ENV_FILE' .env

if command -v python3.11 >/dev/null 2>&1; then
  echo 'python3.11' > '$REMOTE_PYTHON_BIN'
fi

PYTHON_CMD=\"\$(cat '$REMOTE_PYTHON_BIN')\"

if [[ -x '$REMOTE_VENV_DIR/bin/python' ]]; then
  VENV_PY_VERSION=\"\$('$REMOTE_VENV_DIR/bin/python' -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")')\"
  TARGET_PY_VERSION=\"\$(\$PYTHON_CMD -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")')\"
  if [[ \"\$VENV_PY_VERSION\" != \"\$TARGET_PY_VERSION\" ]]; then
    echo \"Recreating virtualenv: existing Python \$VENV_PY_VERSION, target Python \$TARGET_PY_VERSION\"
    rm -rf '$REMOTE_VENV_DIR'
  fi
fi

if [[ ! -d '$REMOTE_VENV_DIR' ]]; then
  \$PYTHON_CMD -m venv '$REMOTE_VENV_DIR'
fi

'$REMOTE_VENV_DIR/bin/pip' install --upgrade pip
'$REMOTE_VENV_DIR/bin/pip' install -r requirements.txt

echo 'Restarting uvicorn...'
pkill -f '[u]vicorn main:app --host 0.0.0.0 --port 8000' || true
sleep 1
touch app.log
setsid '$REMOTE_VENV_DIR/bin/uvicorn' main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 < /dev/null &
sleep 3

if ! pgrep -f '[u]vicorn main:app --host 0.0.0.0 --port 8000' >/dev/null 2>&1; then
  echo 'Uvicorn failed to stay up. app.log:'
  tail -n 120 app.log || true
  exit 1
fi

echo 'Backend restart OK.'
"

echo "[4/4] Cleaning up"
rm -rf "$BUILD_DIR"

echo "Backend deploy complete."
