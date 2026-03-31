#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3000}"

if ! command -v npm >/dev/null 2>&1; then
  echo "[start_web] npm is not available in runtime image"
  echo "[start_web] ensure web service uses Node/Nixpacks build context"
  exit 1
fi

if [[ ! -d web/node_modules ]]; then
  echo "[start_web] installing web dependencies..."
  npm --prefix web ci
fi

if [[ ! -d web/.next ]]; then
  echo "[start_web] building Next.js app..."
  npm --prefix web run build
fi

echo "[start_web] starting Next.js on port ${PORT}..."
exec web/node_modules/.bin/next start web --hostname 0.0.0.0 --port "${PORT}"
