#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

mkdir -p apps/derivaciones/migrations
touch apps/derivaciones/__init__.py apps/derivaciones/migrations/__init__.py

cat > apps/derivaciones/apps.py << 'EOF'
from django.apps import AppConfig


class DerivacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.derivaciones"
    verbose_name = "Derivaciones"
EOF

cat > apps/derivaciones/models.py << 'EOF'
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Derivacion(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        CRITICA = "CRITICA", "Crítica"

    class Estado(models.TextChoices):
        SOLICITADA = "SOLICITADA", "Solicitada"
        ACEPTADA = "ACEPTADA", "Aceptada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        ASIGNADA = "ASIGNADA", "Asignada"
        EN_CAMINO = "EN_CAMINO", "En camino"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episodio = models.ForeignKey(
        "pacientes.Episodio",
        on_delete=models.PROTECT,
        related_name="derivaciones",
    )
    hospital_origen = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        related_name="derivaciones_emitidas",
    )
    hospital_destino = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        related_name="derivaciones_recibidas",
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        db_index=True,
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.SOLICITADA,
        db_index=True,
    )
    motivo = models.TextField()
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="derivaciones_solicitadas",
    )
    aceptada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="derivaciones_aceptadas",
    )
    solicitada_en = models.DateTimeField(default=timezone.now, db_index=True)
    aceptada_en = models.DateTimeField(null=True, blank=True)
    iniciada_en = models.DateTimeField(null=True, blank=True)
    completada_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-solicitada_en"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(hospital_origen=models.F("hospital_destino")),
                name="derivacion_origen_distinto_destino",
            ),
        ]
        indexes = [
            models.Index(fields=["estado", "-solicitada_en"]),
            models.Index(fields=["hospital_origen", "estado"]),
            models.Index(fields=["hospital_destino", "estado"]),
            models.Index(fields=["episodio", "-solicitada_en"]),
        ]
        verbose_name = "derivación"
        verbose_name_plural = "derivaciones"

    def __str__(self):
        return (
            f"{self.hospital_origen.codigo} -> {self.hospital_destino.codigo} "
            f"({self.get_estado_display()})"
        )


class TransicionEstado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    derivacion = models.ForeignKey(
        Derivacion,
        on_delete=models.PROTECT,
        related_name="transiciones",
    )
    estado_anterior = models.CharField(max_length=15, blank=True)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transiciones_derivacion",
    )
    motivo = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["derivacion", "-creado_en"])]
        verbose_name = "transición de estado"
        verbose_name_plural = "transiciones de estado"

    def __str__(self):
        return (
            f"{self.derivacion_id}: "
            f"{self.estado_anterior or 'INICIO'} -> {self.estado_nuevo}"
        )
EOF

python3 - << 'PYEOF'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.triaje.apps.TriajeConfig',\n"
addition = needle + "    'apps.derivaciones.apps.DerivacionesConfig',\n"
if "'apps.derivaciones.apps.DerivacionesConfig'" in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: derivaciones añadido a INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró TriajeConfig")
PYEOF

echo "OK: Fase 7.1 completada (models + INSTALLED_APPS)"
