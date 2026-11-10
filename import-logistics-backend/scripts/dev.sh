#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$BACKEND_DIR/docker/docker-compose.yml"
ENV_FILE="$BACKEND_DIR/.env"
BACKUP_DIR="$BACKEND_DIR/backups"

cd "$BACKEND_DIR"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Error: Install Docker Desktop with Docker Compose v2." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker Desktop is not running." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env is missing. Copy .env.example to .env and configure it." >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Error: Development Compose file not found." >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

validate_config() {
  compose config --quiet
}

usage() {
  cat <<'USAGE'
Usage: ./scripts/dev.sh <command>

  start       Start development services without rebuilding
  build       Build images and start services
  stop        Stop containers without deleting data
  restart     Restart existing containers
  status      Show service status and API readiness
  logs [name] Follow logs, optionally for one service
  backup      Back up PostgreSQL and uploads
  restore DIR Restore PostgreSQL and stage uploads for review
  help        Show this help

Examples:
  ./scripts/dev.sh start
  ./scripts/dev.sh status
  ./scripts/dev.sh logs web
  ./scripts/dev.sh backup
  ./scripts/dev.sh restore ./backups/dev-backup-YYYYMMDD-HHMMSS
USAGE
}

require_running_db() {
  if ! compose ps --status running --services | grep -qx 'db'; then
    echo "Error: Database container is not running. Start the stack first." >&2
    exit 1
  fi
}

case "${1:-help}" in
  start)
    validate_config
    compose up -d
    echo "Development stack started. Checking API readiness..."
    for attempt in {1..15}; do
      if curl --fail --silent http://localhost:8000/ready; then
        printf '\n'
        exit 0
      fi
      sleep 2
    done
    echo "API is not ready yet. Check: ./scripts/dev.sh logs web" >&2
    exit 1
    ;;
  build)
    validate_config
    compose up -d --build
    ;;
  stop)
    compose stop
    echo "Containers stopped. Persistent data has been preserved."
    ;;
  restart)
    compose restart
    ;;
  status)
    compose ps
    printf '\nAPI readiness:\n'
    curl --fail --silent --show-error http://localhost:8000/ready || true
    printf '\n'
    ;;
  logs)
    shift || true
    if [[ $# -gt 0 ]]; then
      compose logs -f --tail=100 "$@"
    else
      compose logs -f --tail=100
    fi
    ;;
  backup)
    validate_config
    require_running_db
    mkdir -p "$BACKUP_DIR"
    stamp="$(date +%Y%m%d-%H%M%S)"
    destination="$BACKUP_DIR/dev-backup-$stamp"
    mkdir -p "$destination"

    echo "Backing up PostgreSQL..."
    compose exec -T db sh -c \
      'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
      > "$destination/database.dump"

    if [[ ! -s "$destination/database.dump" ]]; then
      echo "Error: Database backup is empty." >&2
      exit 1
    fi

    echo "Backing up uploads..."
    tar -czf "$destination/uploads.tar.gz" -C "$BACKEND_DIR" uploads

    echo "Backup completed:"
    echo "$destination"
    ;;
  restore)
    if [[ $# -ne 2 ]]; then
      usage
      exit 2
    fi

    backup_path="$(cd -- "$2" 2>/dev/null && pwd)" || {
      echo "Error: Backup directory not found: $2" >&2
      exit 1
    }

    if [[ ! -s "$backup_path/database.dump" || ! -f "$backup_path/uploads.tar.gz" ]]; then
      echo "Error: Backup must contain database.dump and uploads.tar.gz." >&2
      exit 1
    fi

    validate_config
    require_running_db

    echo "WARNING: This restores database objects from the backup."
    echo "Existing application services will be stopped temporarily."
    read -r -p 'Type RESTORE to continue: ' answer

    if [[ "$answer" != "RESTORE" ]]; then
      echo "Restore cancelled."
      exit 0
    fi

    compose stop web worker-tracking worker-pricing worker-fx-notify celery-beat flower pgbouncer || true

    echo "Restoring PostgreSQL..."
    compose exec -T db sh -c \
      'pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
      < "$backup_path/database.dump"

    restored_uploads="$BACKEND_DIR/uploads-restored-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$restored_uploads"
    tar -xzf "$backup_path/uploads.tar.gz" -C "$restored_uploads" --strip-components=1

    compose up -d

    printf '\nDatabase restore completed.\n'
    printf 'Uploads extracted separately to:\n%s\n' "$restored_uploads"
    echo "Review the restored uploads before merging them into ./uploads."
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac
