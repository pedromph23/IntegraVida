import uuid

from django.conf import settings
from django.db import models


class EventoAuditoria(models.Model):
    class Resultado(models.TextChoices):
        EXITOSO = "EXITOSO", "Exitoso"
        DENEGADO = "DENEGADO", "Denegado"
        ERROR = "ERROR", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocurrido_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos_auditoria",
    )
    organizacion_id = models.UUIDField(null=True, blank=True, db_index=True)
    accion = models.CharField(max_length=100, db_index=True)
    tipo_objeto = models.CharField(max_length=100, blank=True)
    objeto_id = models.CharField(max_length=100, blank=True)
    resultado = models.CharField(
        max_length=10, choices=Resultado.choices, default=Resultado.EXITOSO
    )
    justificacion = models.CharField(max_length=500, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    agente_usuario = models.CharField(max_length=500, blank=True)
    id_correlacion = models.CharField(max_length=100, blank=True, db_index=True)
    metadatos = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-ocurrido_en"]
        indexes = [
            models.Index(fields=["actor", "ocurrido_en"]),
            models.Index(fields=["tipo_objeto", "objeto_id"]),
            models.Index(fields=["resultado", "ocurrido_en"]),
        ]
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self):
        return f"{self.ocurrido_en} — {self.accion} — {self.resultado}"
