import hashlib
import json
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


HASH_GENESIS = "0" * 64


class NotAllowed(Exception):
    """Operación no permitida sobre registros inmutables de auditoría (§7.3)."""


class EventoAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NotAllowed(
            "Los eventos de auditoría son inmutables: update() no permitido."
        )

    def delete(self):
        raise NotAllowed(
            "Los eventos de auditoría son inmutables: delete() no permitido."
        )


class EventoAuditoriaManager(models.Manager.from_queryset(EventoAuditoriaQuerySet)):
    pass


class EventoAuditoria(models.Model):
    class Resultado(models.TextChoices):
        EXITOSO = "EXITOSO", "Exitoso"
        DENEGADO = "DENEGADO", "Denegado"
        ERROR = "ERROR", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ocurrido_en = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
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

    hash_anterior = models.CharField(max_length=64, db_index=True)
    hash_actual = models.CharField(max_length=64, unique=True, db_index=True)

    objects = EventoAuditoriaManager()

    class Meta:
        ordering = ["-ocurrido_en"]
        indexes = [
            models.Index(fields=["actor", "ocurrido_en"]),
            models.Index(fields=["tipo_objeto", "objeto_id"]),
            models.Index(fields=["resultado", "ocurrido_en"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["hash_anterior"],
                name="unique_evento_hash_anterior",
            ),
        ]
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self):
        return f"{self.ocurrido_en} — {self.accion} — {self.resultado}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise NotAllowed(
                "Los eventos de auditoría son inmutables: no se permite "
                "save() sobre un registro existente."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotAllowed(
            "Los eventos de auditoría son inmutables: no se permite delete()."
        )


def calcular_hash(evento):
    """
    Calcula el hash SHA-256 determinista de un EventoAuditoria.

    Incluye todos los campos de dominio + hash_anterior. La serialización
    es canónica (sort_keys, separadores sin espacio) para que dos llamadas
    produzcan siempre el mismo resultado.
    """
    payload = {
        "id": str(evento.id),
        "ocurrido_en": evento.ocurrido_en.isoformat() if evento.ocurrido_en else None,
        "actor_id": str(evento.actor_id) if evento.actor_id else None,
        "organizacion_id": str(evento.organizacion_id) if evento.organizacion_id else None,
        "accion": evento.accion,
        "tipo_objeto": evento.tipo_objeto,
        "objeto_id": evento.objeto_id,
        "resultado": evento.resultado,
        "justificacion": evento.justificacion,
        "direccion_ip": str(evento.direccion_ip) if evento.direccion_ip else None,
        "agente_usuario": evento.agente_usuario,
        "id_correlacion": evento.id_correlacion,
        "metadatos": evento.metadatos,
        "hash_anterior": evento.hash_anterior,
    }
    serialized = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()