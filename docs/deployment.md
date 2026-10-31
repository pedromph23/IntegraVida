# Deployment — IntegraVida

> **Estado:** preparado para producción, deployment real diferido.
> **Proveedor:** a elegir cuando se autorice (Render, Railway, Fly.io,
> DigitalOcean, VPS propio con PostgreSQL 17 + PostGIS 3.5).

## 1. Requisitos del proveedor

Cualquier proveedor debe cumplir:

- PostgreSQL 17 con PostGIS 3.5 (o compatible)
- Python 3.13
- Proceso WSGI persistente (Gunicorn o similar)
- Volumen persistente para `MEDIA_ROOT` (adjuntos)
- Variables de entorno seguras (nunca en código)
- HTTPS con certificado válido
- Backups automatizados de PostgreSQL
- Logs accesibles
- SSH o `console` para operaciones

Proveedores verificados:

- **Render**: PostgreSQL 17 + PostGIS sí. Web service + background worker.
- **Railway**: PostgreSQL 16 + PostGIS. Simple, $5/mes.
- **Fly.io**: PostgreSQL 17 con volumen. Requiere más configuración.
- **DigitalOcean App Platform**: PostgreSQL 17 + PostGIS. $12+/mes.
- **VPS propio (Hetzner/DO)**: control total, más trabajo operativo.

**No recomendado**: Vercel, Netlify (serverless, sin proceso WSGI persistente).

## 2. Variables de entorno requeridas

En el panel del proveedor, configurar:

    DJANGO_SECRET_KEY=<generar nueva, 50 chars aleatorios>
    DJANGO_DEBUG=False
    DJANGO_ALLOWED_HOSTS=integravida.example.com
    DJANGO_CSRF_TRUSTED_ORIGINS=https://integravida.example.com

    DB_NAME=<nombre del panel>
    DB_USER_APP=integravida_app
    DB_PASSWORD_APP=<contraseña fuerte, 32 chars>
    DB_USER_MIGRATOR=integravida_migrator
    DB_PASSWORD_MIGRATOR=<contraseña fuerte, 32 chars>
    DB_HOST=<host del panel>
    DB_PORT=5432

    FIELD_ENCRYPTION_KEY=<generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
    PACIENTE_CEDULA_HMAC_KEY=<generar nueva>

    EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
    EMAIL_HOST=<SMTP del proveedor>
    EMAIL_HOST_USER=<usuario SMTP>
    EMAIL_HOST_PASSWORD=<password SMTP>
    EMAIL_PORT=587
    EMAIL_USE_TLS=True

    DJANGO_LOG_LEVEL=WARNING

## 3. Procedimiento de deployment

### 3.1 Preparación inicial (una vez)

1. Crear cuenta y proyecto en el proveedor.
2. Crear PostgreSQL 17 + PostGIS.
3. Configurar variables de entorno (sección 2).
4. Conectar el repositorio Git al proveedor.
5. Añadir comando de build:

    pip install -r requirements.txt
    python manage.py collectstatic --noinput

6. Añadir comando de release (antes de servir):

    python manage.py migrate --settings=config.settings
    # Nota: Django lee DB_USER_APP por defecto.
    # Para migrate se necesita DB_USER=integravida_migrator.
    # Ver sección 4.

7. Comando de start:

    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

### 3.2 Deployment regular

Cada push a `main`:

1. Build (instala deps, collectstatic).
2. Migración (con migrator).
3. Reinicia gunicorn (con app).
4. Smoke test: `curl https://dominio/api/publico/emergencias/`

## 4. Migraciones con rol separado

El comando de release del proveedor **no debe** usar `DB_USER_APP`. Opciones:

### Opción A — Comando custom

    # En el proveedor, configurar:
    release_command = "scripts/migrate_prod.sh"

    # scripts/migrate_prod.sh
    #!/bin/bash
    export DB_USER=$DB_USER_MIGRATOR
    export DB_PASSWORD=$DB_PASSWORD_MIGRATOR
    python manage.py migrate --noinput

### Opción B — Variable temporal

    DB_USER=$DB_USER_MIGRATOR DB_PASSWORD=$DB_PASSWORD_MIGRATOR \
        python manage.py migrate --noinput

### Opción C — settings distintos

Crear `config/settings_migrations.py` que herede de `config.settings` y
sobrescriba `DATABASES['default']['USER']` con `DB_USER_MIGRATOR`. Uso:

    python manage.py migrate --settings=config.settings_migrations

**Recomendación: Opción B**, con el comando de release inline.

## 5. Primer arranque

Una vez desplegado:

1. **Verificar health check público:**
   curl https://dominio/api/publico/emergencias/
   # Esperado: {"total": 0, "limite": 50, "offset": 0, "resultados": []}

2. **Crear superusuario:**
   En el proveedor, abrir consola interactiva:
   python manage.py createsuperuser

3. **Aplicar setup_pg_roles.sql** si no se aplicó antes del deployment:
   sudo -u postgres psql -d integravida_db -f scripts/setup_pg_roles.sql

   (En proveedores managed sin sudo, usar el SQL con el usuario admin que
   proporcione el panel.)

4. **Verificar HTTPS:** abrir navegador, comprobar candado y HSTS.

5. **Verificar backups:** el proveedor debe tener backup diario activado.

## 6. Verificación post-deployment

Lista de checks (todos deben pasar):

- [ ] `curl https://dominio/api/publico/emergencias/` → 200 JSON
- [ ] `curl https://dominio/api/publico/refugios/` → 200 JSON
- [ ] `curl https://dominio/api/publico/hospitales/` → 200 JSON
- [ ] `curl -I https://dominio/admin/` → 302 (redirect a login)
- [ ] `curl -I http://dominio/` → 301 (redirect a HTTPS)
- [ ] Header `Strict-Transport-Security` presente
- [ ] Header `X-Content-Type-Options: nosniff` presente
- [ ] Cookie `sessionid` tiene flag `Secure`
- [ ] `python manage.py check --deploy` sin warnings críticos
- [ ] Logs muestran `INFO` normales, sin `Traceback`
- [ ] Backups automáticos activados (verificar en panel)
- [ ] `FIELD_ENCRYPTION_KEY` guardada en gestor de contraseñas aparte

## 7. Rollback

Si deployment falla:

1. En el panel, "Rollback to previous deploy" (todos los proveedores lo tienen).
2. Si la migración causó el problema, revertir con `migrate <app> <migración_anterior>`.
3. Si es crítico, restaurar desde backup (ver `docs/operations.md`).

## 8. Proveedores descartados y por qué

- **Vercel**: serverless, no soporta WSGI persistente ni PostGIS.
- **Netlify**: idem.
- **Heroku**: deprecated free tier, requiere tarjeta.
- **PythonAnywhere**: sin PostGIS en free tier.

## 9. Referencias

- `docs/operations.md` — runbook y backup.
- `docs/audit-and-security.md` — §7.3 separación de privilegios.
- `docs/privacy-and-retention.md` — retención y cifrado.
- `scripts/setup_pg_roles.sql` — setup de roles PG.
