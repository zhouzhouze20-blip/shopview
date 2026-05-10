#!/usr/bin/env sh
set -eu

cd /app
export PYTHONPATH="/app/python_app:/app:${PYTHONPATH:-}"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  (
    cd /app/python_app
    ./alembic_upgrade.sh
  )
fi

exec "$@"
