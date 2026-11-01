import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.pacientes.fields import EncryptedCharField


class Usuario(AbstractUser):
    """Cuenta de acceso de una persona en IntegraVida."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    # ── MFA del admin oculto (F4.b) ──
    # Secret TOTP cifrado at-rest. null/None = no enrolado.
    # Generado por `manage.py crear_admin_inicial` o por la vista
    # /<INTEGRAVIDA_ADMIN_SLUG>/mfa/setup/.
    admin_mfa_secret = EncryptedCharField(
        max_length=500, null=True, blank=True, default=None,
    )
    admin_mfa_enrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=~models.Q(email=""),
                name="unique_usuario_email_nonempty",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username
