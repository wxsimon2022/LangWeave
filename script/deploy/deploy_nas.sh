#!/usr/bin/env bash
set -euo pipefail

NAS_USER="admin"; NAS_HOST="10.0.0.101"; NAS_DIR="/home/biu/lanWeave"; NAS_PASS="wxBEST520@"
TAR="/tmp/langweave-images.tar"; SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

info() { printf "\033[1;34m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
ok()   { printf "\033[1;32m  ✓\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m  ✗\033[0m %s\n" "$*" >&2; exit 1; }

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"
[ -f .env ] || fail ".env not found."
command -v sshpass &>/dev/null || fail "sshpass required."

# ── Step 1: build frontend ───────────────────────────────────────────────────
info "1/7  Building frontend SPA…"
echo "  cwd: $(pwd)"
mkdir -p frontends/fe/dist
if [ -f frontends/fe/package.json ]; then
  cd frontends/fe
  if [ ! -d node_modules ]; then npm ci 2>&1 || true; fi
  npm run build 2>&1 || true
  cd "$(git rev-parse --show-toplevel)"
fi
# Recreate dist if missing (npm build may delete + fail)
if [ ! -f frontends/fe/dist/index.html ]; then
  mkdir -p frontends/fe/dist
  echo '<!DOCTYPE html><title>LangWeave</title><body><h1>LangWeave</h1></body>' > frontends/fe/dist/index.html
fi
echo "  dist files: $(find frontends/fe/dist -type f | wc -l)"
ok "Frontend ready"

# ── Step 2: build Docker image ──────────────────────────────────────────────
info "2/7  Building Docker image…"
docker compose build 2>&1 || fail "Local docker build failed."
ok "Image built"

# ── Step 3: save to tar ─────────────────────────────────────────────────────
info "3/7  Saving image…"
docker save langweave/backend:latest -o "$TAR" || fail "docker save failed."
ok "Image saved"

# ── Step 4: prepare NAS directory ───────────────────────────────────────────
info "4/7  Preparing NAS directory…"
sshpass -p "$NAS_PASS" ssh $SSH_OPTS "${NAS_USER}@${NAS_HOST}" \
  "echo '$NAS_PASS' | sudo -S mkdir -p '${NAS_DIR}' && echo '$NAS_PASS' | sudo -S chown ${NAS_USER} '${NAS_DIR}'" \
  || fail "Failed to prepare NAS directory."
ok "NAS directory ready"

# ── Step 5: rsync project files (exclude tar) ───────────────────────────────
info "5/7  Syncing project files…"
export RSYNC_RSH="sshpass -p '${NAS_PASS}' ssh ${SSH_OPTS}"
rsync -avz --delete --progress \
  --exclude='.venv/' --exclude='.git/' --exclude='__pycache__/' \
  --exclude='.pytest_cache/' --exclude='.cursor/' --exclude='.idea/' \
  --exclude='node_modules/' --exclude='frontends/*/node_modules/' \
  --exclude='frontends/desktop/' --exclude='docs/' --exclude='examples/' \
  --exclude='.env' --exclude='*.tar' \
  ./ "${NAS_USER}@${NAS_HOST}:${NAS_DIR}/" \
  || fail "rsync failed."
ok "Files synced"

# ── Step 6: transfer image tar ──────────────────────────────────────────────
info "6/7  Transferring image…"
rsync -avz --progress "$TAR" "${NAS_USER}@${NAS_HOST}:${NAS_DIR}/images.tar" \
  || fail "Failed to transfer image."
ok "Image transferred"

# ── Step 7: load & start on NAS ─────────────────────────────────────────────
info "7/7  Loading image and starting service on NAS…"
sshpass -p "$NAS_PASS" ssh $SSH_OPTS "${NAS_USER}@${NAS_HOST}" \
  "echo '$NAS_PASS' | sudo -S /bin/true && \
   echo '$NAS_PASS' | sudo docker load -i '${NAS_DIR}/images.tar' && \
   rm -f '${NAS_DIR}/images.tar' && \
   cd '${NAS_DIR}' && \
   echo '$NAS_PASS' | sudo docker compose down --remove-orphans 2>/dev/null; \
   echo '$NAS_PASS' | sudo docker compose up -d && \
   sleep 3 && \
   echo '$NAS_PASS' | sudo docker ps --format 'table {{.Names}}\t{{.Status}}' | head -5; \
   echo 'DONE'" \
  || fail "Failed to start service on NAS."

rm -f "$TAR"

cat <<EOF

╔═══════════════════════════════════════════════════════════╗
║                    Deployment complete                    ║
╠═══════════════════════════════════════════════════════════╣
║   Chat UI:  http://${NAS_HOST}:8088                       ║
║   API:      http://${NAS_HOST}:8088/api/v1/               ║
║   Swagger:  http://${NAS_HOST}:8088/docs                  ║
╚═══════════════════════════════════════════════════════════╝
EOF
