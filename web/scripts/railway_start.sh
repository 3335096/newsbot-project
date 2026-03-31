#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3000}"

if [[ ! -d node_modules ]]; then
  echo "[web/railway_start] installing dependencies..."
  npm ci
fi

if [[ ! -d .next ]]; then
  echo "[web/railway_start] building Next.js app..."
  npm run build
fi

echo "[web/railway_start] starting Next.js on port ${PORT}..."
exec npx --yes next start --hostname 0.0.0.0 --port "${PORT}"
