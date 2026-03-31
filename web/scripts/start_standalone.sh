#!/usr/bin/env bash
set -euo pipefail

# Next.js standalone server expects static/public assets relative to
# .next/standalone. In some builders they stay in project root.
if [[ -d ".next/static" ]]; then
  mkdir -p ".next/standalone/.next"
  rm -rf ".next/standalone/.next/static"
  cp -R ".next/static" ".next/standalone/.next/static"
fi

if [[ -d "public" ]]; then
  rm -rf ".next/standalone/public"
  cp -R "public" ".next/standalone/public"
fi

exec env HOSTNAME="0.0.0.0" PORT="${PORT:-3000}" node ".next/standalone/server.js"
