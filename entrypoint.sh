#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/v1/models /data/v2/models /data/v2/reports

if [ ! -f /data/v1/student_burnout_lab4.db ]; then
  echo "[entrypoint] Seeding v1 SQLite database..."
  cp /srv/v1/data/student_burnout_lab4.db /data/v1/student_burnout_lab4.db
fi

if [ ! -f /data/v2/student_burnout_lab4.db ]; then
  echo "[entrypoint] Seeding v2 SQLite database..."
  cp /srv/v2/data/student_burnout_lab4.db /data/v2/student_burnout_lab4.db
fi

if [ ! -L /srv/v2/reports ]; then
  if [ -d /srv/v2/reports ] && [ -z "$(ls -A /data/v2/reports)" ]; then
    cp -a /srv/v2/reports/. /data/v2/reports/
  fi
  rm -rf /srv/v2/reports
  ln -s /data/v2/reports /srv/v2/reports
fi

echo "[entrypoint] Starting v1 (main / Lab 4) on :8001..."
(
  cd /srv/v1
  export LEARNWELL_DB_PATH=/data/v1/student_burnout_lab4.db
  export LEARNWELL_MODEL_PATH=/data/v1/models/burnout_logistic_regression.joblib
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*'
) &
PID_V1=$!

echo "[entrypoint] Starting v2 (lab5 / Lab 5) on :8002..."
(
  cd /srv/v2
  export LEARNWELL_DB_PATH=/data/v2/student_burnout_lab4.db
  export LEARNWELL_MODEL_PATH=/data/v2/models/burnout_logistic_regression.joblib
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*'
) &
PID_V2=$!

cleanup() {
  echo "[entrypoint] Shutting down v1 and v2..."
  kill -TERM "$PID_V1" "$PID_V2" 2>/dev/null || true
  wait "$PID_V1" "$PID_V2" 2>/dev/null || true
}
trap cleanup TERM INT

wait -n "$PID_V1" "$PID_V2"
STATUS=$?
echo "[entrypoint] One of the services exited with status ${STATUS}, stopping container."
cleanup
exit "$STATUS"
