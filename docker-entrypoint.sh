#!/usr/bin/env sh
set -eu

app_root="${APP_ROOT:-/app}"
cd "$app_root"
export PYTHONPATH="${app_root}/python_app:${app_root}:${PYTHONPATH:-}"

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying database migrations..."
  migration_attempt=1
  migration_max_attempts="${MIGRATION_MAX_ATTEMPTS:-12}"
  migration_retry_delay="${MIGRATION_RETRY_DELAY_SECONDS:-5}"

  while :; do
    if migration_output="$(
      cd "$app_root/python_app"
      ./alembic_upgrade.sh 2>&1
    )"; then
      printf '%s\n' "$migration_output"
      break
    else
      migration_status=$?
      printf '%s\n' "$migration_output" >&2

      if ! printf '%s\n' "$migration_output" | grep -Eqi \
        'too many clients|could not connect to server|connection refused|connection timed out|timeout expired'; then
        echo "Database migration failed with a non-retryable error." >&2
        exit "$migration_status"
      fi

      if [ "$migration_attempt" -ge "$migration_max_attempts" ]; then
        echo "Database migration failed after ${migration_attempt} attempts." >&2
        exit "$migration_status"
      fi

      echo "Database connection is busy; retrying migration in ${migration_retry_delay}s (${migration_attempt}/${migration_max_attempts})..." >&2
      migration_attempt=$((migration_attempt + 1))
      sleep "$migration_retry_delay"
    fi
  done
else
  echo "Skipping database migrations. Set RUN_MIGRATIONS=true to run them on startup."
fi

exec "$@"
