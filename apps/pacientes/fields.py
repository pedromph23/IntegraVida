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

class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    """TextField que cifra el valor en la base de datos."""
    pass
