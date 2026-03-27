#!/usr/bin/env bash
set -euo pipefail

# Railway injects PORT for web services.
PORT="${PORT:-8000}"

# Some platforms expose Postgres URL as postgres://...
# SQLAlchemy expects postgresql://...
if [[ "${DATABASE_URL:-}" == postgres://* ]]; then
  export DATABASE_URL="postgresql://${DATABASE_URL#postgres://}"
fi

echo "[start_api] running migrations..."
if python -m alembic upgrade head; then
  echo "[start_api] migrations applied"
else
  echo "[start_api] alembic failed, fallback init_db.py"
  python scripts/init_db.py
fi

echo "[start_api] starting uvicorn on port ${PORT}..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
