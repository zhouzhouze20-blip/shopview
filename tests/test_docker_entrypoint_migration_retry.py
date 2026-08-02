import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = REPO_ROOT / "docker-entrypoint.sh"


def _write_fake_migration(tmp_path: Path, script: str) -> Path:
    app_root = tmp_path / "app"
    migration_script = app_root / "python_app" / "alembic_upgrade.sh"
    migration_script.parent.mkdir(parents=True)
    migration_script.write_text(script, encoding="utf-8")
    migration_script.chmod(0o755)
    return app_root


def test_entrypoint_retries_transient_database_connection_failure(tmp_path):
    app_root = _write_fake_migration(
        tmp_path,
        """#!/usr/bin/env sh
count_file=\"$(dirname \"$0\")/attempts\"
attempts=0
[ ! -f \"$count_file\" ] || attempts=\"$(cat \"$count_file\")\"
attempts=$((attempts + 1))
printf '%s' \"$attempts\" > \"$count_file\"
if [ \"$attempts\" -lt 3 ]; then
  echo 'FATAL: sorry, too many clients already' >&2
  exit 1
fi
echo 'migration complete'
""",
    )
    env = {
        **os.environ,
        "APP_ROOT": str(app_root),
        "RUN_MIGRATIONS": "true",
        "MIGRATION_MAX_ATTEMPTS": "3",
        "MIGRATION_RETRY_DELAY_SECONDS": "0",
    }

    result = subprocess.run(
        ["/bin/sh", str(ENTRYPOINT), "true"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert (app_root / "python_app" / "attempts").read_text() == "3"
    assert "Database connection is busy; retrying migration" in result.stderr
    assert "migration complete" in result.stdout


def test_entrypoint_does_not_retry_non_connection_migration_failure(tmp_path):
    app_root = _write_fake_migration(
        tmp_path,
        """#!/usr/bin/env sh
echo 'alembic revision graph is invalid' >&2
exit 7
""",
    )
    env = {
        **os.environ,
        "APP_ROOT": str(app_root),
        "RUN_MIGRATIONS": "true",
        "MIGRATION_MAX_ATTEMPTS": "3",
        "MIGRATION_RETRY_DELAY_SECONDS": "0",
    }

    result = subprocess.run(
        ["/bin/sh", str(ENTRYPOINT), "true"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 7
    assert "non-retryable error" in result.stderr
