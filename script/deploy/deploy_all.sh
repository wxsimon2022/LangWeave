#!/usr/bin/env bash
set -euo pipefail

# One-click deployment script:
# - build frontend
# - prepare backend + frontend + SSL release dir
# - rsync to remote host
# - sync directly to remote current dir
# - install/update dependencies
# - restart uvicorn
# - validate and reload nginx
#
# Production env file: .env.prod (root of project)
# Local dev env file: .env (NOT included in release)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/script/deploy/build"
RELEASE_DIR="$BUILD_DIR/release"
FRONTEND_DIR="$ROOT_DIR/fe"
REMOTE_HOST="root@124.223.72.223"
REMOTE_APP_DIR="/home/biu/chat"
REMOTE_NGINX_DIR="/usr/local/nginx/conf/vhost"
REMOTE_CURRENT_DIR="$REMOTE_APP_DIR/current"
REMOTE_ENV_FILE="$REMOTE_APP_DIR/shared/.env"
REMOTE_SHARED_DIR="$REMOTE_APP_DIR/shared"
REMOTE_VENV_DIR="$REMOTE_SHARED_DIR/.venv"
REMOTE_PYTHON_BIN="$REMOTE_SHARED_DIR/python-bin"

echo "[1/7] Building frontend"
rm -rf "$BUILD_DIR"
mkdir -p "$RELEASE_DIR"
cd "$FRONTEND_DIR"
npm run build

echo "[2/7] Preparing release bundle"
cd "$ROOT_DIR"
mkdir -p "$RELEASE_DIR/frontend" "$RELEASE_DIR/ssl"
rsync -a \
  --exclude ".git" \
  --exclude ".idea" \
  --exclude ".pytest_cache" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "fe/node_modules" \
  --exclude "fe/dist" \
  --exclude "script/deploy/build" \
  --exclude ".env" \
  --exclude ".env.prod" \
  app langweave tests main.py pyproject.toml requirements.txt README.md .env.example \
  "$RELEASE_DIR/"
# Include .env.prod as the production env template (rsync excludes it above)
mkdir -p "$RELEASE_DIR/config"
cp "$ROOT_DIR/.env.prod" "$RELEASE_DIR/config/.env.prod"
rsync -a "$FRONTEND_DIR/dist/" "$RELEASE_DIR/frontend/"
cp "$ROOT_DIR"/script/chat.mybfs.cn_nginx/chat.mybfs.cn.key "$RELEASE_DIR/ssl/"
cp "$ROOT_DIR"/script/chat.mybfs.cn_nginx/chat.mybfs.cn_bundle.pem "$RELEASE_DIR/ssl/"
cp "$ROOT_DIR"/script/chat.mybfs.cn_nginx/chat.mybfs.cn_bundle.crt "$RELEASE_DIR/ssl/"

echo "[3/7] Preparing remote directories"
ssh "$REMOTE_HOST" "
set -euo pipefail

mkdir -p '$REMOTE_SHARED_DIR' '$REMOTE_CURRENT_DIR'
"

echo "[4/7] Rsync release files"
rsync -az --delete "$RELEASE_DIR/" "$REMOTE_HOST:$REMOTE_CURRENT_DIR/"

echo "[5/7] Rsync nginx config"
rsync -az "$ROOT_DIR/script/deploy/nginx.chat.mybfs.cn.conf" \
  "$REMOTE_HOST:$REMOTE_NGINX_DIR/chat.mybfs.cn.conf"

echo "[6/7] Running remote deployment"
ssh "$REMOTE_HOST" "
set -euo pipefail

if [[ ! -f '$REMOTE_ENV_FILE' ]]; then
  if [[ -f '$REMOTE_CURRENT_DIR/config/.env.prod' ]]; then
    cp '$REMOTE_CURRENT_DIR/config/.env.prod' '$REMOTE_ENV_FILE'
    echo 'Created $REMOTE_ENV_FILE from config/.env.prod.'
  else
    cp '$REMOTE_CURRENT_DIR/.env.example' '$REMOTE_ENV_FILE'
    echo 'Created $REMOTE_ENV_FILE from .env.example (config/.env.prod not found).'
  fi
fi

if [[ -f '$REMOTE_CURRENT_DIR/config/.env.prod' ]]; then
  cp '$REMOTE_CURRENT_DIR/config/.env.prod' '$REMOTE_SHARED_DIR/.env.prod'
  echo 'Synced .env.prod to shared for reference.'
fi

cd '$REMOTE_CURRENT_DIR'
ln -sfn '$REMOTE_ENV_FILE' .env

if command -v python3.11 >/dev/null 2>&1; then
  echo 'Using existing python3.11'
  echo 'python3.11' > '$REMOTE_PYTHON_BIN'
else
  echo 'python3.11 not found. Installing via dnf...'
  dnf install -y --disablerepo=docker-ce-stable python3.11 python3.11-devel
  echo 'python3.11' > '$REMOTE_PYTHON_BIN'
fi

PYTHON_CMD=\"\$(cat '$REMOTE_PYTHON_BIN')\"
\$PYTHON_CMD --version

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

/usr/local/nginx/sbin/nginx -t
/usr/local/nginx/sbin/nginx -s reload
"

echo "[7/7] Deployment complete"
cat <<EOF
One-click deploy finished.

Current directory:
  $REMOTE_CURRENT_DIR

Shared env file:
  $REMOTE_ENV_FILE (from config/.env.prod on first deploy)

Shared .env.prod (reference):
  $REMOTE_SHARED_DIR/.env.prod

Shared venv:
  $REMOTE_VENV_DIR

Useful remote checks:
  tail -n 200 $REMOTE_CURRENT_DIR/app.log
  ps -ef | grep 'uvicorn main:app'
  /usr/local/nginx/sbin/nginx -t
EOF