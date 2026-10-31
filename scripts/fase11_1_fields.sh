#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

# ── 0) Instalar cryptography si no está ─────────────────────────
if ! python3 -c "import cryptography" 2>/dev/null; then
    echo "Instalando cryptography..."
    pip install cryptography
    pip freeze > requirements.txt
    echo "OK: cryptography instalada y requirements.txt actualizado"
else
    echo "OK: cryptography ya instalada"
fi

# ── 1) Generar FIELD_ENCRYPTION_KEY si no existe ────────────────
if ! grep -q "^FIELD_ENCRYPTION_KEY=" .env 2>/dev/null; then
    KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "" >> .env
    echo "FIELD_ENCRYPTION_KEY=$KEY" >> .env
    echo "OK: FIELD_ENCRYPTION_KEY generada y añadida a .env"
else
    echo "ya aplicado: FIELD_ENCRYPTION_KEY en .env"
fi

# ── 2) Crear apps/pacientes/fields.py ───────────────────────────
cat > apps/pacientes/fields.py << 'PYEOF'
"""Campos cifrados para datos clínicos y personales (§11).

Diseño:
- Cifrado simétrico con Fernet (AES-128-CBC + HMAC-SHA256).
- La clave vive en FIELD_ENCRYPTION_KEY (independiente de SECRET_KEY
  para permitir rotación sin invalidar sesiones).
- from_db_value tolera datos legacy en plaintext (InvalidToken →
  retorna el valor tal cual). Esto permite migraciones incrementales.
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _get_fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY debe estar definido en settings (vía .env)."
        )
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


class EncryptedFieldMixin:
    """Cifra al escribir, descifra al leer."""

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, Exception):
            # Dato legacy en plaintext o clave distinta.
            return value

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return _get_fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    """CharField que cifra el valor en la base de datos."""
    pass


class EncryptedEmailField(EncryptedFieldMixin, models.EmailField):
    """EmailField que cifra el valor en la base de datos."""
    pass
PYEOF

echo "OK: apps/pacientes/fields.py creado"

# ── 3) Añadir FIELD_ENCRYPTION_KEY a settings.py ────────────────
python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")

needle = 'SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")\n'
addition = (
    needle
    + '\n# Clave para cifrado de campos clínicos (§11).\n'
    + '# Independiente de SECRET_KEY: permite rotación sin invalidar sesiones.\n'
    + 'FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")\n'
)
if "FIELD_ENCRYPTION_KEY" in text:
    print("ya aplicado: FIELD_ENCRYPTION_KEY en settings.py")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: FIELD_ENCRYPTION_KEY en settings.py")
else:
    raise SystemExit("ERROR: marker SECRET_KEY no encontrado")
PY

# ── 4) Documentar en .env.example ───────────────────────────────
if ! grep -q "^FIELD_ENCRYPTION_KEY=" .env.example 2>/dev/null; then
    cat >> .env.example << 'EOF'

# Clave Fernet (44 chars base64). Generar con:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Cifra campos CLI: Paciente.cedula, nombres, apellidos, telefono, email.
# SI SE PIERDE: los datos cifrados son ilegibles. Respaldar con pg_dump
# junto con la BD.
FIELD_ENCRYPTION_KEY=
EOF
    echo "OK: .env.example actualizado"
else
    echo "ya aplicado: .env.example"
fi

# ── 5) Verificar imports ────────────────────────────────────────
echo ""
echo "▶ Verificación"
python3 manage.py shell -c "from apps.pacientes.fields import EncryptedCharField, EncryptedEmailField; print('OK: fields importan')"
