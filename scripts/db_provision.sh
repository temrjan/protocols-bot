#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
INIT_SQL="$PROJECT_ROOT/db/init.sql"

if [ ! -f "$ENV_FILE" ]; then
  echo ".env not found at $ENV_FILE" >&2
  exit 1
fi

if [ ! -f "$INIT_SQL" ]; then
  echo "SQL schema file not found at $INIT_SQL" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -z "${DB_PATH:-}" ]]; then
  echo "DB_PATH must be set in .env" >&2
  exit 1
fi

DB_DIR="$(dirname "$DB_PATH")"
mkdir -p "$DB_DIR"

sqlite3 "$DB_PATH" < "$INIT_SQL"
