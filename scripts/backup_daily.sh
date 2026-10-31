#!/usr/bin/env bash
# Backup diario de integravida_db (§1.2 de docs/operations.md).
# Carga .env de forma segura (sin `source`) — soporta caracteres especiales.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../.env}"

# ── Cargar .env línea a línea (safe parser) ───────────────────────
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            \#*|"") continue ;;
        esac
        key="${line%%=*}"
        value="${line#*=}"
        key="$(printf '%s' "$key" | tr -d '[:space:]')"
        if [ -z "${!key:-}" ]; then
            export "$key=$value"
        fi
    done < "$ENV_FILE"
else
    echo "ADVERTENCIA: no se encontró $ENV_FILE" >&2
fi

DB_NAME="${DB_NAME:-integravida_db}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER_MIGRATOR:-${DB_USER:-integravida}}"
DB_PASS="${DB_PASSWORD_MIGRATOR:-${DB_PASSWORD:-}}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/integravida}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

if [ -z "$DB_PASS" ]; then
    echo "ERROR: DB_PASSWORD o DB_PASSWORD_MIGRATOR vacío en $ENV_FILE" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/integravida_${TIMESTAMP}.dump"
SHA_FILE="$BACKUP_FILE.sha256"

echo "[$(date -Iseconds)] Iniciando backup de $DB_NAME → $BACKUP_FILE"

PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F c \
    --no-owner \
    -f "$BACKUP_FILE"

echo "[$(date -Iseconds)] pg_dump OK ($(stat -c%s "$BACKUP_FILE") bytes)"

sha256sum "$BACKUP_FILE" > "$SHA_FILE"
echo "[$(date -Iseconds)] SHA-256: $(cat "$SHA_FILE")"

DELETED=0
while IFS= read -r OLD; do
    rm -f "$OLD" "$OLD.sha256"
    DELETED=$((DELETED + 1))
done < <(find "$BACKUP_DIR" -name "integravida_*.dump" -type f \
         -mtime +"$RETENTION_DAYS" 2>/dev/null || true)

echo "[$(date -Iseconds)] Rotación: $DELETED backups eliminados (>${RETENTION_DAYS}d)"
echo "[$(date -Iseconds)] Backup diario completo"
