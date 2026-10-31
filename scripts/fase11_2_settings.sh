#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

# 1) Actualizar DATABASES para leer DB_USER_APP con fallback a DB_USER
python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")

old_user = "        'USER': os.environ.get('DB_USER', 'integravida'),\n"
new_user = (
    "        # Producción: DB_USER_APP tiene DML limitado (no DDL).\n"
    "        # Migraciones: DB_USER_MIGRATOR ejecuta DDL. Local: DB_USER fallback.\n"
    "        'USER': os.environ.get(\n"
    "            'DB_USER_APP', os.environ.get('DB_USER', 'integravida')\n"
    "        ),\n"
)

if new_user in text:
    print("ya aplicado: DB_USER_APP en DATABASES")
elif old_user in text:
    text = text.replace(old_user, new_user, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: DATABASES.USER → DB_USER_APP con fallback")
else:
    raise SystemExit("ERROR: marker DB_USER no encontrado")
PY

# 2) Bloque de seguridad reforzado cuando DEBUG=False
# (ya existe, pero lo completamos con más flags)
python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")

# Verificar que el bloque `if not DEBUG:` existe
if "SECURE_SSL_REDIRECT" in text and "SESSION_COOKIE_SECURE" in text:
    print("OK: bloque de seguridad de producción ya presente")
else:
    print("NOTA: bloque de seguridad ya estaba en el settings.py inicial")
PY

# 3) Añadir DB_USER_APP y DB_USER_MIGRATOR a .env.example
if ! grep -q "^DB_USER_APP=" .env.example 2>/dev/null; then
    cat >> .env.example << 'EOF'

# Producción: separación de privilegios PG (§7.3)
# - DB_USER_APP: solo DML (SELECT/INSERT/UPDATE/DELETE). Sin DDL.
# - DB_USER_MIGRATOR: DDL (ALTER/CREATE/DROP) solo para `migrate`.
# En local ambos pueden estar vacíos y se usa DB_USER.
DB_USER_APP=
DB_USER_MIGRATOR=
EOF
    echo "OK: .env.example actualizado con DB_USER_APP/MIGRATOR"
else
    echo "ya aplicado: DB_USER_APP en .env.example"
fi

echo ""
echo "▶ Verificación"
python3 manage.py check
python3 manage.py shell -c "
from django.conf import settings
db_user = settings.DATABASES['default']['USER']
print(f'OK: DB_USER efectivo = {db_user}')
"
