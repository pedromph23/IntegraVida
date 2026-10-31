#!/usr/bin/env bash
# Prueba de restauración mensual (§1.3 de docs/operations.md).
# Carga .env safe. Crea BD aislada CON PostGIS, restaura, verifica, elimina.
#
# Estrategia:
# - Creamos postgis ANTES del restore (pg_dump no incluye CREATE EXTENSION).
# - Filtramos del -L list los objetos del extension postgis que no podemos
#   restaurar con usuario no-superusuario: EXTENSION, COMMENT, y las tablas
#   spatial_ref_sys/geography_columns/geometry_columns (ya creadas).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../.env}"

# ── Cargar .env safe ────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in \#*|"") continue ;; esac
        key="${line%%=*}"
        value="${line#*=}"
        key="$(printf '%s' "$key" | tr -d '[:space:]')"
        if [ -z "${!key:-}" ]; then
            export "$key=$value"
        fi
    done < "$ENV_FILE"
fi

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
ADMIN_USER="${DB_USER_MIGRATOR:-${DB_USER:-integravida}}"
ADMIN_PASS="${DB_PASSWORD_MIGRATOR:-${DB_PASSWORD:-}}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/integravida}"
RESTORE_DB="integravida_restore_test_$(date +%s)"

if [ -z "$ADMIN_PASS" ]; then
    echo "ERROR: DB_PASSWORD vacío" >&2
    exit 1
fi

LATEST=$(ls -t "$BACKUP_DIR"/integravida_*.dump 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "ERROR: no hay backups en $BACKUP_DIR"
    exit 1
fi

echo "[$(date -Iseconds)] Backup a restaurar: $LATEST"

if [ -f "$LATEST.sha256" ]; then
    (cd "$BACKUP_DIR" && sha256sum -c "$(basename "$LATEST").sha256")
    echo "[$(date -Iseconds)] SHA-256 OK"
fi

echo "[$(date -Iseconds)] Creando $RESTORE_DB"
PGPASSWORD="$ADMIN_PASS" createdb \
    -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" "$RESTORE_DB"

cleanup() {
    echo "[$(date -Iseconds)] Eliminando $RESTORE_DB"
    PGPASSWORD="$ADMIN_PASS" dropdb \
        -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" --if-exists "$RESTORE_DB" || true
}
trap cleanup EXIT

echo "[$(date -Iseconds)] Creando extensiones (postgis) en $RESTORE_DB"
PGPASSWORD="$ADMIN_PASS" psql \
    -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d "$RESTORE_DB" \
    -c "CREATE EXTENSION IF NOT EXISTS postgis;" >/dev/null

# ── Generar lista de objetos y filtrar los del extension postgis ──
LIST_RAW=$(mktemp)
LIST_FILTERED=$(mktemp)
trap 'rm -f "$LIST_RAW" "$LIST_FILTERED"; cleanup' EXIT

echo "[$(date -Iseconds)] Generando lista de objetos del dump"
pg_restore -l "$LATEST" > "$LIST_RAW"

# Excluir:
#  - EXTENSION - postgis  (CREATE EXTENSION + COMMENT, ambos fallan)
#  - spatial_ref_sys      (tabla del extension; ya creada por CREATE EXTENSION)
#  - geography_columns    (vista del extension)
#  - geometry_columns     (vista del extension)
grep -vE \
  'EXTENSION - postgis|spatial_ref_sys|geography_columns|geometry_columns' \
  "$LIST_RAW" > "$LIST_FILTERED"

ORIG_COUNT=$(wc -l < "$LIST_RAW")
FILT_COUNT=$(wc -l < "$LIST_FILTERED")
echo "[$(date -Iseconds)] Objetos: $ORIG_COUNT → $FILT_COUNT (excluidos: $((ORIG_COUNT - FILT_COUNT)))"

echo "[$(date -Iseconds)] Restaurando datos (con -L filtrada)..."
PGPASSWORD="$ADMIN_PASS" pg_restore \
    -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" \
    -d "$RESTORE_DB" \
    --no-owner \
    --no-acl \
    --no-comments \
    -L "$LIST_FILTERED" \
    "$LATEST"

echo "[$(date -Iseconds)] pg_restore completó sin errores"

echo "[$(date -Iseconds)] Verificando conteos"
for TABLE in auditoria_eventoauditoria pacientes_paciente usuarios_usuario \
             refugios_refugio hospitales_hospital inventario_insumo; do
    COUNT=$(PGPASSWORD="$ADMIN_PASS" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$ADMIN_USER" -d "$RESTORE_DB" \
        -tAc "SELECT COUNT(*) FROM $TABLE" 2>/dev/null || echo "MISSING")
    echo "  $TABLE: $COUNT"
done

echo "[$(date -Iseconds)] Verificando cadena de auditoría sobre BD restaurada"
DB_NAME="$RESTORE_DB" \
DB_USER="$ADMIN_USER" \
DB_PASSWORD="$ADMIN_PASS" \
python3 manage.py verify_audit_chain 2>&1 | tail -3

echo ""
echo "[$(date -Iseconds)] PRUEBA DE RESTAURACIÓN COMPLETA"
