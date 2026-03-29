#!/usr/bin/env bash
set -euo pipefail

# Unified Railway start entrypoint for multi-service deployments from one repo.
# Priority:
# 1) APP_ROLE env var (explicit override)
# 2) RAILWAY_SERVICE_NAME (service name in Railway)
# 3) fallback to api
role="${APP_ROLE:-${RAILWAY_SERVICE_NAME:-api}}"
role="$(printf "%s" "${role}" | tr '[:upper:]' '[:lower:]')"

case "${role}" in
  worker)
    echo "[railway_start] role=worker"
    exec python -m worker
    ;;
  bot)
    echo "[railway_start] role=bot"
    exec python -m bot.main
    ;;
  *)
    echo "[railway_start] role=api"
    exec bash scripts/start_api.sh
    ;;
esac
