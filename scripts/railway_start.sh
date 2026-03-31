#!/usr/bin/env bash
set -euo pipefail

# Unified Railway start entrypoint for multi-service deployments from one repo.
# Priority:
# 1) APP_ROLE env var (explicit override)
# 2) RAILWAY_SERVICE_NAME (service name in Railway)
# 3) fallback to api
raw_role="${APP_ROLE:-${RAILWAY_SERVICE_NAME:-api}}"
role="$(printf "%s" "${raw_role}" | tr '[:upper:]' '[:lower:]')"

# Railway service names are often not exactly "api"/"worker"/"bot"
# (e.g. "newsbot-worker", "api-web"). Match by token boundaries to avoid
# false positives like "newsbot-project" -> "bot".
if [[ "${role}" =~ (^|[^a-z0-9])worker([^a-z0-9]|$) ]]; then
  role="worker"
elif [[ "${role}" =~ (^|[^a-z0-9])bot([^a-z0-9]|$) ]]; then
  role="bot"
elif [[ "${role}" =~ (^|[^a-z0-9])web([^a-z0-9]|$) ]]; then
  role="web"
elif [[ "${role}" =~ (^|[^a-z0-9])api([^a-z0-9]|$) ]]; then
  role="api"
fi

case "${role}" in
  worker)
    echo "[railway_start] role=worker"
    exec python -m worker
    ;;
  bot)
    echo "[railway_start] role=bot"
    exec python -m bot.main
    ;;
  web)
    echo "[railway_start] role=web"
    exec bash scripts/start_web.sh
    ;;
  *)
    echo "[railway_start] role=api (raw='${raw_role}')"
    exec bash scripts/start_api.sh
    ;;
esac
