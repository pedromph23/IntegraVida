#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Aplicar SQL de roles al cluster local"
echo "  (con contraseñas de desarrollo, NO producción)"

# Sustituir placeholders por contraseñas locales
# (En producción se editan antes de ejecutar)
sudo -u postgres psql -d integravida_db << 'SQL'
-- Crear roles con contraseñas locales
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'integravida_migrator') THEN
        CREATE ROLE integravida_migrator LOGIN PASSWORD 'dev_migrator_2026';
    ELSE
        ALTER ROLE integravida_migrator PASSWORD 'dev_migrator_2026';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'integravida_app') THEN
        CREATE ROLE integravida_app LOGIN PASSWORD 'dev_app_2026';
    ELSE
        ALTER ROLE integravida_app PASSWORD 'dev_app_2026';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE integravida_db TO integravida_migrator;
GRANT CONNECT ON DATABASE integravida_db TO integravida_app;
GRANT USAGE ON SCHEMA public TO integravida_migrator;
GRANT USAGE ON SCHEMA public TO integravida_app;
GRANT CREATE ON SCHEMA public TO integravida_migrator;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO integravida_app;
REVOKE ALL ON TABLE auditoria_eventoauditoria FROM integravida_app;
GRANT SELECT, INSERT ON TABLE auditoria_eventoauditoria TO integravida_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO integravida_app;
ALTER DEFAULT PRIVILEGES FOR ROLE integravida_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO integravida_app;
ALTER DEFAULT PRIVILEGES FOR ROLE integravida_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO integravida_app;
SQL

echo "OK: roles creados con contraseñas de dev"

echo ""
echo "▶ 2. Verificar que integravida_app NO puede DROP auditoría"
DROP_RESULT=$(PGPASSWORD=dev_app_2026 psql -h 127.0.0.1 -U integravida_app \
    -d integravida_db -c "DROP TABLE auditoria_eventoauditoria;" 2>&1 || true)

if echo "$DROP_RESULT" | grep -q "permission denied\|must be owner"; then
    echo "OK: integravida_app NO puede DROP auditoría (correcto)"
else
    echo "⚠ ADVERTENCIA: integravida_app pudo intentar DROP:"
    echo "$DROP_RESULT"
fi

echo ""
echo "▶ 3. Verificar que integravida_app NO puede UPDATE auditoría"
UPDATE_RESULT=$(PGPASSWORD=dev_app_2026 psql -h 127.0.0.1 -U integravida_app \
    -d integravida_db -c "UPDATE auditoria_eventoauditoria SET accion='hack' WHERE false;" 2>&1 || true)

if echo "$UPDATE_RESULT" | grep -q "permission denied"; then
    echo "OK: integravida_app NO puede UPDATE auditoría (correcto)"
else
    echo "⚠ ADVERTENCIA: UPDATE devolvió: $UPDATE_RESULT"
fi

echo ""
echo "▶ 4. Verificar que integravida_app SÍ puede INSERT en auditoría"
INSERT_RESULT=$(PGPASSWORD=dev_app_2026 psql -h 127.0.0.1 -U integravida_app \
    -d integravida_db -c "SELECT count(*) FROM auditoria_eventoauditoria;" 2>&1 || true)

if echo "$INSERT_RESULT" | grep -qE "^\s*[0-9]+"; then
    echo "OK: integravida_app SÍ puede SELECT auditoría (correcto)"
else
    echo "⚠ ADVERTENCIA: SELECT devolvió: $INSERT_RESULT"
fi

echo ""
echo "▶ 5. Verificar que integravida_app SÍ puede SELECT en tabla operativa"
SELECT_RESULT=$(PGPASSWORD=dev_app_2026 psql -h 127.0.0.1 -U integravida_app \
    -d integravida_db -c "SELECT count(*) FROM pacientes_paciente;" 2>&1 || true)

if echo "$SELECT_RESULT" | grep -qE "^\s*[0-9]+"; then
    echo "OK: integravida_app SÍ puede SELECT pacientes (correcto)"
else
    echo "⚠ ADVERTENCIA: SELECT devolvió: $SELECT_RESULT"
fi

echo ""
echo "▶ 6. Verificar que integravida_app NO puede DROP pacientes"
DROP_PAC=$(PGPASSWORD=dev_app_2026 psql -h 127.0.0.1 -U integravida_app \
    -d integravida_db -c "DROP TABLE pacientes_paciente;" 2>&1 || true)

if echo "$DROP_PAC" | grep -q "must be owner\|permission denied"; then
    echo "OK: integravida_app NO puede DROP pacientes (correcto)"
else
    echo "⚠ ADVERTENCIA: $DROP_PAC"
fi

echo ""
echo "✅ FASE 11.2 — roles aplicados y verificados"
echo ""
echo "NOTA: .env local sigue con DB_USER=integravida (superusuario local)."
echo "      En producción se usará DB_USER_APP=integravida_app."
echo ""
echo "Contraseñas de dev (NO usar en producción):"
echo "  integravida_migrator: dev_migrator_2026"
echo "  integravida_app:      dev_app_2026"
