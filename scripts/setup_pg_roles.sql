-- ============================================================
-- IntegraVida — Setup de roles PostgreSQL (Fase 11.2)
-- Ejecutar como superusuario postgres en producción:
--   sudo -u postgres psql -d integravida_db -f scripts/setup_pg_roles.sql
-- ADVERTENCIA: antes de ejecutar en producción, hacer pg_dump.
-- Idempotente: usa IF NOT EXISTS, no borra roles existentes.
-- ============================================================

-- 1. Rol migrator: DDL + DML. Dueño de las tablas futuras.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'integravida_migrator') THEN
        CREATE ROLE integravida_migrator LOGIN PASSWORD 'CAMBIAR_EN_PRODUCCION';
    END IF;
END
$$;

-- 2. Rol app: solo DML en tablas operativas.
-- En auditoria_eventoauditoria: SELECT + INSERT, NUNCA UPDATE/DELETE.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'integravida_app') THEN
        CREATE ROLE integravida_app LOGIN PASSWORD 'CAMBIAR_EN_PRODUCCION';
    END IF;
END
$$;

-- 3. Permisos de conexión a la BD
GRANT CONNECT ON DATABASE integravida_db TO integravida_migrator;
GRANT CONNECT ON DATABASE integravida_db TO integravida_app;

-- 4. Permisos de schema
GRANT USAGE ON SCHEMA public TO integravida_migrator;
GRANT USAGE ON SCHEMA public TO integravida_app;

-- 5. MIGRATOR: dueño del schema public (puede crear tablas en migraciones)
-- ADVERTENCIA: solo ejecutar si quieres que migrator sea dueño del schema.
-- En algunos hostings no se permite. Alternativa: GRANT ALL.
GRANT CREATE ON SCHEMA public TO integravida_migrator;

-- 6. APP: DML en tablas operativas existentes
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO integravida_app;

-- 7. APP: SOLO SELECT + INSERT en auditoría (nunca UPDATE/DELETE)
REVOKE ALL ON TABLE auditoria_eventoauditoria FROM integravida_app;
GRANT SELECT, INSERT ON TABLE auditoria_eventoauditoria TO integravida_app;

-- 8. APP: secuencias (necesarias para INSERT)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO integravida_app;

-- 9. Aplicar a tablas futuras (creadas por migrator)
ALTER DEFAULT PRIVILEGES FOR ROLE integravida_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO integravida_app;
ALTER DEFAULT PRIVILEGES FOR ROLE integravida_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO integravida_app;

-- 10. Excepción para futuras tablas de auditoría (nombradas *_eventoauditoria*)
-- No se puede hacer ALTER DEFAULT PRIVILEGES por patrón. Documentado en
-- docs/deployment.md: cuando se cree una tabla nueva *_auditoria*, revocar
-- UPDATE/DELETE explícitamente de integravida_app.
