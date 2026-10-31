# Operaciones — IntegraVida

> **Estado:** runbook para operación diaria post-deployment.
> **Público:** responsable técnico de la instancia.

## 1. Backup de la base de datos

### 1.1 Backup manual

    pg_dump -h DB_HOST -U integravida_migrator -d integravida_db \
        -F c -f /backups/integravida_$(date +%Y%m%d_%H%M%S).dump

`-F c` = formato custom (comprimido, permite restore parcial con `pg_restore`).

### 1.2 Backup automatizado (cron diario)

    # /etc/cron.d/integravida-backup
    0 3 * * * integravida /opt/integravida/scripts/backup_daily.sh >> /var/log/integravida-backup.log 2>&1

El script `scripts/backup_daily.sh`:

1. Ejecuta `pg_dump -F c`.
2. Calcula SHA-256 del archivo.
3. Copia a almacenamiento off-site (S3, rsync, etc.).
4. Rota backups >30 días.
5. Registra en log.

### 1.3 Prueba de restauración (mensual)

**Obligatorio** probar restauración al menos una vez al mes:

    bash scripts/restore_test.sh

El script automatiza:
1. Toma el backup más reciente de `$BACKUP_DIR`.
2. Verifica su SHA-256.
3. Crea BD aislada `integravida_restore_test_<timestamp>`.
4. Aplica `CREATE EXTENSION postgis` (pg_dump no la incluye).
5. Genera lista de objetos con `pg_restore -l`.
6. Filtra objetos del extension postgis que no se pueden restaurar
   con usuario no-superusuario:
   - `EXTENSION - postgis` (ya existe)
   - `COMMENT - EXTENSION postgis` (requiere owner)
   - `spatial_ref_sys`, `geography_columns`, `geometry_columns`
7. Restaura con `pg_restore -L <lista_filtrada>`.
8. Verifica conteos de tablas clave.
9. Ejecuta `python manage.py verify_audit_chain` sobre la BD restaurada.
10. Elimina la BD temporal.

**Criterios de aceptación:**

- [ ] SHA-256 OK
- [ ] `pg_restore completó sin errores` en el log
- [ ] Conteos de tablas clave coinciden con producción
- [ ] `verify_audit_chain` retorna `OK: cadena íntegra`
- [ ] La BD temporal se elimina

Si la cadena de hashes falla → investigar inmediatamente (ver §7 del
`docs/audit-and-security.md`).
