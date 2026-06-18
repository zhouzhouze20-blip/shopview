#!/usr/bin/env sh
set -eu

cd /app
export PYTHONPATH="/app/python_app:/app:${PYTHONPATH:-}"

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  (
    cd /app/python_app
    ./alembic_upgrade.sh
  )
else
  echo "Skipping database migrations. Set RUN_MIGRATIONS=true to run them on startup."
fi

exec "$@"
