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

    # En BD aislada (NUNCA en producción)
    createdb -h localhost -U postgres integravida_restore_test
    pg_restore -h localhost -U postgres -d integravida_restore_test \
        /backups/integravida_20261031_030000.dump

    # Verificar integridad
    psql -h localhost -U postgres -d integravida_restore_test \
        -c "SELECT COUNT(*) FROM auditoria_eventoauditoria;"
    psql -h localhost -U postgres -d integravida_restore_test \
        -c "SELECT COUNT(*) FROM pacientes_paciente;"

    # Verificar cadena de auditoría
    python manage.py shell -c "
    from apps.auditoria.models import EventoAuditoria, calcular_hash
    ultimo = EventoAuditoria.objects.order_by('-ocurrido_en').first()
    assert calcular_hash(ultimo) == ultimo.hash_actual, 'Cadena rota'
    print('OK: cadena de auditoría íntegra')
    "

    # Eliminar BD de prueba
    dropdb -h localhost -U postgres integravida_restore_test

Si la cadena de hashes falla → investigar inmediatamente (ver §7 del
`docs/audit-and-security.md`).

## 2. Backup de FIELD_ENCRYPTION_KEY

**CRÍTICO.** La pérdida de esta clave = datos cifrados irrecuperables.

### 2.1 Obtención

    grep "^FIELD_ENCRYPTION_KEY=" /opt/integravida/.env
    # Copiar el valor (44 chars base64)

### 2.2 Almacenamiento

Guardar en **mínimo 2 lugares**:

1. **Gestor de contraseñas** (1Password, Bitwarden, KeePassXC).
2. **Sobre físico sellado** en oficina de la organización.
3. (Opcional) Caja fuerte digital con control dual.

**Nunca** en:
- Repositorio Git.
- Email.
- Slack/WhatsApp.
- Servidor de aplicación (solo en `.env`).

### 2.3 Verificación anual

Una vez al año, restaurar un backup en BD aislada, arrancar la app con la
clave guardada, y verificar que `Paciente.objects.first().nombres` se
descifra correctamente. Si falla, la clave guardada está mal.

## 3. Rotación de FIELD_ENCRYPTION_KEY

Si la clave se ve comprometida, rotar. **Procedimiento irreversible sin
backup previo:**

1. **Backup completo antes de empezar:**

       pg_dump -F c -f /backups/pre_rotation.dump ...
       sha256sum /backups/pre_rotation.dump > /backups/pre_rotation.sha256

2. **Guardar la clave vieja** como `FIELD_ENCRYPTION_KEY_OLD`.

3. **Generar nueva clave:**

       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

4. **Descifrar con vieja, cifrar con nueva.** Comando `rotate_encryption_key`
   (a implementar en Fase 11.4 si es necesario). Esqueleto:

       #!/bin/bash
       # scripts/rotate_encryption_key.py
       # 1. Leer FIELD_ENCRYPTION_KEY_OLD
       # 2. Leer FIELD_ENCRYPTION_KEY (nueva)
       # 3. Por cada Paciente:
       #    - Descifrar campos con vieja
       #    - Cifrar con nueva
       #    - save()
       # 4. Verificar roundtrip

5. **Verificar** que todos los registros se leen con la nueva clave.

6. **Actualizar backups de la clave** (sobrescribir los anteriores).

7. **Documentar el incidente** en `docs/incidents/YYYY-MM-DD-key-rotation.md`.

## 4. Monitoreo diario

### 4.1 Health check

    curl -s https://dominio/api/publico/emergencias/ | head -1
    # Esperado: {"total": ...

    curl -s -o /dev/null -w "%{http_code}" https://dominio/api/publico/emergencias/
    # Esperado: 200

### 4.2 Logs a revisar

- **Errores 500**: `grep '" 500 ' /var/log/integravida/access.log`
- **Errores 4xx anómalos**: picos de 401 o 403 indican intentos de acceso.
- **Auditoría fallida**: `grep 'auditoria.*error' /var/log/integravida/*.log`
- **Conexiones PG rechazadas**: `grep 'FATAL' /var/log/postgresql/*.log`

### 4.3 Métricas a vigilar

- Uso de disco (BD + backups).
- Tamaño de `auditoria_eventoauditoria` (crece sin límite — retención §3
  de `audit-and-security.md`).
- Tiempo de respuesta del portal público (<500ms esperado).
- Conexiones activas a PG (max_connections).

## 5. Incidentes comunes

### 5.1 PostgreSQL no responde

    systemctl status postgresql
    sudo -u postgres pg_isready
    sudo -u postgres psql -c "SELECT 1"

Si falla: verificar espacio en disco, reiniciar servicio, revisar logs.

### 5.2 La app devuelve 500

1. Revisar logs: `tail -100 /var/log/integravida/error.log`.
2. Si es `OperationalError` de conexión → PG caído.
3. Si es `ImproperlyConfigured` → variable de entorno faltante.
4. Si es `DecryptionError` → `FIELD_ENCRYPTION_KEY` incorrecta.

### 5.3 Auditoría reporta cadena rota

Comando de verificación (a implementar en Fase 11.4):

    python manage.py verify_audit_chain

Si falla:
1. **Detener escritura** (modo mantenimiento).
2. Notificar al responsable de seguridad.
3. Comparar con backup más reciente.
4. Reconstruir cadena desde el último evento íntegro conocido.
5. Documentar en `docs/incidents/`.

### 5.4 Disco lleno

    df -h
    du -sh /var/lib/postgresql/*
    du -sh /opt/integravida/media/*

Acciones:
- Rotar backups viejos (>30 días).
- Archivar `auditoria_eventoauditoria` (nunca borrar — mover a almacenamiento frío).
- Limpiar `media/` de adjuntos obsoletos según retención.

## 6. Actualización de código

    cd /opt/integravida
    git fetch origin
    git log HEAD..origin/main --oneline
    # Revisar commits antes de aplicar
    git pull origin main
    pip install -r requirements.txt
    python manage.py migrate --settings=config.settings  # con migrator
    python manage.py collectstatic --noinput
    sudo systemctl restart integravida.service
    # Smoke test
    curl -s -o /dev/null -w "%{http_code}" https://dominio/api/publico/emergencias/

## 7. Contactos de emergencia

(Llenar cuando la instancia entre en producción)

- Responsable técnico: <nombre, teléfono>
- Responsable institucional: <nombre, teléfono>
- Proveedor de hosting: <soporte, teléfono>
- Responsable de privacidad: <nombre, email>

## 8. Referencias

- `docs/deployment.md` — procedimiento inicial.
- `docs/audit-and-security.md` — política de auditoría.
- `docs/privacy-and-retention.md` — retención y cifrado.
- `docs/migration-plan.md` — migración de datos.
- `docs/incidents/` — post-mortems (crear cuando haya).
