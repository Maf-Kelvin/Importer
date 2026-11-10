#!/usr/bin/env bash
# Prove the migrations work on a real, empty PostgreSQL.
# Needs: `pip install -r requirements-dev.txt` (in a virtualenv), plus EITHER Docker OR your own PostgreSQL.
#
#   bash scripts/verify_migrations.sh                       # starts a throw-away PostgreSQL with Docker
#   VERIFY_DATABASE_URL=postgresql+asyncpg://me@localhost:5432/importer_check \
#   VERIFY_CONFIRM_DISPOSABLE=yes bash scripts/verify_migrations.sh   # use a PostgreSQL you already have
#
# It checks four things, in order:
#   1. alembic upgrade head     the migrations build a clean database
#   2. alembic check            the database now matches the models exactly (no missing/extra columns)
#   3. alembic downgrade base   every migration can be undone (this DROPS the tables)
#   4. alembic upgrade head     ...and applied again (+ check)
#
# If step 2 reports differences, the baseline file is slightly off. Fix it by adding a follow-up migration:
#   alembic revision --autogenerate -m "sync with models"
# (only while NO real database has applied 001_baseline.py may you edit/regenerate that file instead).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v alembic >/dev/null 2>&1; then
  echo "alembic is not installed. In a virtualenv run:  pip install -r requirements-dev.txt"
  exit 1
fi

NAME=importer-migration-check
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }

if [ -n "${VERIFY_DATABASE_URL:-}" ]; then
  # ---- use an existing PostgreSQL ----
  if [ "${VERIFY_CONFIRM_DISPOSABLE:-}" != "yes" ]; then
    echo "VERIFY_DATABASE_URL is set. Step 3 DROPS every table in that database."
    echo "Use an empty, disposable database, then re-run with VERIFY_CONFIRM_DISPOSABLE=yes"
    exit 1
  fi
  export DATABASE_URL="$VERIFY_DATABASE_URL"
else
  # ---- throw-away PostgreSQL in Docker ----
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    cat <<'MSG'
Docker is not available (is Docker Desktop installed and running?).

Option A - start Docker Desktop, wait until it says "running", check with `docker info`, then re-run this script.

Option B - use PostgreSQL directly (macOS with Homebrew):
    brew install postgresql@16 && brew services start postgresql@16
    createdb importer_check
    VERIFY_DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/importer_check" \
    VERIFY_CONFIRM_DISPOSABLE=yes bash scripts/verify_migrations.sh
MSG
    exit 1
  fi
  trap cleanup EXIT
  cleanup
  docker run -d --rm --name "$NAME" -e POSTGRES_PASSWORD=check -e POSTGRES_DB=check \
    -p 55433:5432 postgres:16-alpine >/dev/null
  echo "Waiting for PostgreSQL..."
  for _ in $(seq 1 40); do
    docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1 && break
    sleep 1
  done
  export DATABASE_URL="postgresql+asyncpg://postgres:check@localhost:55433/check"
fi

export ENVIRONMENT=development
unset ALEMBIC_DATABASE_URL

echo "1/4 upgrade head";               alembic upgrade head
echo "2/4 check (models vs database)"; alembic check
echo "3/4 downgrade base";             alembic downgrade base
echo "4/4 upgrade head again";         alembic upgrade head && alembic check
echo
echo "OK: migrations build, match the models, undo and re-apply cleanly."
