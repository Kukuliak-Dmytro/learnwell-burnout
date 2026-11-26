#!/usr/bin/env bash
set -euo pipefail

# Run this script from your local machine (same LAN as 192.168.0.103),
# OR run the remote block directly on 192.168.0.103.
# Usage:
#   ./deploy-to-server.sh
#   SSH_USER=setup SERVER_HOST=192.168.0.103 ./deploy-to-server.sh

SERVER_HOST="${SERVER_HOST:-192.168.0.103}"
SSH_USER="${SSH_USER:-setup}"
REMOTE_DIR="${REMOTE_DIR:-~/learnwell-burnout-deploy}"
REPO_URL="https://github.com/Kukuliak-Dmytro/learnwell-burnout.git"

echo "==> Deploying learnwell-burnout (v1 + v2) and updating Nginx on ${SSH_USER}@${SERVER_HOST}"

ssh -t "${SSH_USER}@${SERVER_HOST}" bash -s <<EOF
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

echo "==> Waiting for v1 (:8001) and v2 (:8002) health checks..."
for i in \$(seq 1 40); do
  if curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8002/health >/dev/null 2>&1; then
    echo "==> Container services are UP!"
    break
  fi
  if [ "\$i" -eq 40 ]; then
    echo "ERROR: Services did not respond within 40s. Check: docker logs learnwell-burnout"
    exit 1
  fi
  sleep 1
done

echo "==> Upgrading nginx and applying v1smart/v2smart config..."
sudo apt-get update
sudo apt-get install --only-upgrade -y nginx
sudo cp ${REMOTE_DIR}/nginx-dvkpowered.conf /etc/nginx/sites-available/learnwell-burnout.conf
sudo ln -sf /etc/nginx/sites-available/learnwell-burnout.conf /etc/nginx/sites-enabled/learnwell-burnout.conf
sudo nginx -t
sudo systemctl reload nginx

echo "==> Verifying Nginx routing on port 80..."
echo -n "v1smart.dvkpowered.org -> "
curl -fsS -H "Host: v1smart.dvkpowered.org" http://127.0.0.1/health
echo ""
echo -n "v2smart.dvkpowered.org -> "
curl -fsS -H "Host: v2smart.dvkpowered.org" http://127.0.0.1/health
echo ""
echo "==> Done! Nginx version:"
nginx -v
EOF
