#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$ROOT_DIR/alembic.ini"

# Find a usable python interpreter with alembic installed.
PYTHON_BIN="${ALEMBIC_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in \
    "$ROOT_DIR/../venv/bin/python" \
    "$ROOT_DIR/../venv/bin/python3" \
    "$ROOT_DIR/../.venv/bin/python" \
    "$ROOT_DIR/../.venv/bin/python3"; do
    if [[ -x "$candidate" ]]; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python not found. Set ALEMBIC_PYTHON to a valid interpreter." >&2
  exit 1
fi

# Decide upgrade target: if multiple heads, default to 'heads'.
HEAD_COUNT=0
if HEADS_OUT="$($PYTHON_BIN -m alembic -c "$CONFIG_FILE" heads 2>/dev/null)"; then
  HEAD_COUNT=$(printf "%s" "$HEADS_OUT" | awk 'NF{count++} END{print count+0}')
fi

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  if [[ "$HEAD_COUNT" -gt 1 ]]; then
    TARGET="heads"
  else
    TARGET="head"
  fi
fi

exec "$PYTHON_BIN" -m alembic -c "$CONFIG_FILE" upgrade "$TARGET"
