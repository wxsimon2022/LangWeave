#!/usr/bin/env bash
# =============================================================================
# deploy_nas.sh — Deploy LangWeave to a NAS via Docker.
#
# Builds images LOCALLY (bypasses NAS's broken Docker mirror),
# then transfers and loads them on the NAS.
#
# Usage:  ./script/deploy/deploy_nas.sh
# =============================================================================
set -euo pipefail

NAS_USER="admin"
NAS_HOST="10.0.0.101"
NAS_DIR="/home/biu/lanWeave"
NAS_PASS="wxBEST520@"
TAR="/tmp/langweave-images.tar"
COMPOSE_PROJECT="langweave"
BACKEND_IMAGE="${COMPOSE_PROJECT}/backend:latest"
NGINX_IMAGE="${COMPOSE_PROJECT}/nginx:latest"

info()  { printf "\033[1;34m[%s]\033[0m %s\n" "$(date +%H:%M:%S)" "$*"; }
ok()    { printf "\033[1;32m  ✓\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m  ⚠\033[0m %s\n" "$*" >&2; }
fail()  { printf "\033[1;31m  ✗\033[0m %s\n" "$*" >&2; exit 1; }

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"
[ -f .env ] || fail ".env not found."
command -v sshpass &>/dev/null || fail "sshpass required (brew install sshpass)."
command -v docker &>/dev/null || fail "Docker required locally for building."

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
SUDO="echo '$NAS_PASS' | setsid sudo -S"

# ── Step 1: build images locally ─────────────────────────────────────────────
info "1/6  Building images locally…"
docker compose build 2>&1 || fail "Local docker build failed."
ok "Images built"

# ── Step 2: save images to tar ───────────────────────────────────────────────
info "2/6  Saving images to ${TAR}…"
docker save "${BACKEND_IMAGE}" "${NGINX_IMAGE}" -o "${TAR}" || fail "docker save failed."
ok "Images saved (${TAR})"

# ── Step 3: prepare remote directory ─────────────────────────────────────────
info "3/6  Preparing remote directory on NAS…"
sshpass -p "$NAS_PASS" ssh ${SSH_OPTS} "${NAS_USER}@${NAS_HOST}" \
  "$SUDO mkdir -p '${NAS_DIR}' && $SUDO chown ${NAS_USER} '${NAS_DIR}'" \
  || fail "Failed."
ok "Remote directory ready"

# ── Step 4: rsync project source + images.tar ────────────────────────────────
info "4/6  Syncing project files…"
export RSYNC_RSH="sshpass -p '${NAS_PASS}' ssh ${SSH_OPTS}"
rsync -avz --delete --progress \
  --exclude='.venv/' --exclude='.git/' --exclude='__pycache__/' \
  --exclude='.pytest_cache/' --exclude='.cursor/' --exclude='.idea/' \
  --exclude='node_modules/' --exclude='frontends/fe/node_modules/' \
  --exclude='frontends/admin/node_modules/' --exclude='frontends/desktop/' \
  --exclude='docs/' --exclude='examples/' --exclude='.env' \
  --exclude='*.tar' \
  ./ "${NAS_USER}@${NAS_HOST}:${NAS_DIR}/" \
  || fail "rsync failed."
ok "Source files synced"

# ── Step 5: transfer images.tar ──────────────────────────────────────────────
info "5/6  Transferring image tar…"
rsync -avz --progress "${TAR}" "${NAS_USER}@${NAS_HOST}:${NAS_DIR}/images.tar" \
  || fail "Failed to transfer images.tar."
ok "Image tar transferred"

# ── Step 6: load images & start on NAS ───────────────────────────────────────
info "6/6  Loading images and starting service on NAS…"
sshpass -p "$NAS_PASS" ssh ${SSH_OPTS} "${NAS_USER}@${NAS_HOST}" \
  "$SUDO /bin/true && \
   $SUDO docker load -i '${NAS_DIR}/images.tar' && \
   $SUDO rm -f '${NAS_DIR}/images.tar' && \
   cd '${NAS_DIR}' && \
   $SUDO docker compose down --remove-orphans 2>/dev/null; \
   $SUDO docker compose up -d && \
   sleep 3 && \
   $SUDO docker ps --format 'table {{.Names}}\t{{.Status}}' | head -5; \
   echo 'DONE'" \
  || fail "Failed to start service on NAS."

# Clean up local tar
rm -f "${TAR}"

cat <<EOF

╔═══════════════════════════════════════════════════════════╗
║                    Deployment complete                    ║
╠═══════════════════════════════════════════════════════════╣
║   Chat UI:  http://${NAS_HOST}:8088                      ║
║   API:      http://${NAS_HOST}:8088/api/v1/              ║
║   Swagger:  http://${NAS_HOST}:8088/docs                 ║
╚═══════════════════════════════════════════════════════════╝
EOF
