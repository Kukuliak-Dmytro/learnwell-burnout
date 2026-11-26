#!/usr/bin/env bash
set -euo pipefail

# Run this script from your local machine that has SSH access to 192.168.0.103.
# Usage:
#   SSH_USER=dmytro ./deploy-to-server.sh
#   (defaults to current user if SSH_USER is not set)

SERVER_HOST="${SERVER_HOST:-192.168.0.103}"
SSH_USER="${SSH_USER:-$USER}"
REMOTE_DIR="${REMOTE_DIR:-~/learnwell-burnout-deploy}"
REPO_URL="https://github.com/Kukuliak-Dmytro/learnwell-burnout.git"

echo "==> Deploying learnwell-burnout (v1 + v2 single container) to ${SSH_USER}@${SERVER_HOST}:${REMOTE_DIR}"

ssh "${SSH_USER}@${SERVER_HOST}" bash -s <<EOF
set -euo pipefail
if [ ! -d ${REMOTE_DIR} ]; then
  git clone --branch deploy --single-branch "${REPO_URL}" ${REMOTE_DIR}
else
  cd ${REMOTE_DIR}
  git fetch origin deploy
  git reset --hard origin/deploy
fi

cd ${REMOTE_DIR}
docker compose up -d --build --force-recreate

echo "==> Waiting for health checks..."
for i in \$(seq 1 30); do
  if curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8002/health >/dev/null 2>&1; then
    echo "==> Both v1 (:8001) and v2 (:8002) are UP!"
    exit 0
  fi
  sleep 1
done

echo "WARNING: Services did not respond within 30s. Check logs: docker logs learnwell-burnout"
exit 1
EOF
