#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

mkdir -p apps/configuracion/migrations
touch apps/configuracion/__init__.py apps/configuracion/migrations/__init__.py

cat > apps/configuracion/apps.py << 'EOF'
from django.apps import AppConfig


class ConfiguracionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.configuracion"
    verbose_name = "Configuración"
EOF

cat > apps/configuracion/models.py << 'EOF'
import uuid

from django.conf import settings
from django.db import models


class ReferenciaMigracion(models.Model):
    """Trazabilidad de cada registro importado desde un sistema de origen.

    §16 exige conservar procedencia: qué sistema origen, qué entidad,
    qué identificador original, hash del registro y resultado de
    validación. Sin esto, no hay forma de auditar migraciones.
    """
    class SistemaOrigen(models.TextChoices):
        COBIJO_VZLA = "COBIJO_VZLA", "Cobijo VZLA"
        DERIVACION_HOSPITALARIA = "DERIVACION_HOSPITALARIA", "Derivación hospitalaria"
        NUTRILINK = "NUTRILINK", "NUTRILINK"

    class ResultadoValidacion(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VALIDADO = "VALIDADO", "Validado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        CON_ADVERTENCIA = "CON_ADVERTENCIA", "Validado con advertencia"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sistema_origen = models.CharField(
        max_length=30, choices=SistemaOrigen.choices, db_index=True,
    )
    entidad_origen = models.CharField(
        max_length=100,
        help_text="Nombre de la tabla/modelo original (ej. 'supplies').",
    )
    identificador_origen = models.CharField(
        max_length=200,
        help_text="PK original en el sistema de origen.",
    )
    entidad_destino = models.CharField(
        max_length=100,
        help_text="Nombre del modelo Django de destino (ej. 'inventario.Insumo').",
    )
    identificador_destino = models.UUIDField(
        null=True, blank=True, db_index=True,
    )
    hash_origen = models.CharField(
        max_length=64, blank=True,
        help_text="SHA-256 del JSON serializado del registro original.",
    )
    resultado_validacion = models.CharField(
        max_length=20, choices=ResultadoValidacion.choices,
        default=ResultadoValidacion.PENDIENTE, db_index=True,
    )
    detalle_validacion = models.TextField(
        blank=True,
        help_text="Advertencias, errores o discrepancias detectadas.",
    )
    migrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="referencias_migracion",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["sistema_origen", "entidad_origen", "identificador_origen"],
                name="unique_referencia_migracion",
            ),
        ]
        indexes = [
            models.Index(fields=["sistema_origen", "resultado_validacion"]),
            models.Index(fields=["entidad_destino", "identificador_destino"]),
        ]
        verbose_name = "referencia de migración"
        verbose_name_plural = "referencias de migración"

    def __str__(self):
        return (
            f"{self.sistema_origen}/{self.entidad_origen}#"
            f"{self.identificador_origen} → {self.entidad_destino}"
        )
EOF

python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
needle = "    'apps.reportes.apps.ReportesConfig',\n"
addition = needle + "    'apps.configuracion.apps.ConfiguracionConfig',\n"
if "'apps.configuracion.apps.ConfiguracionConfig'" in text:
    print("ya aplicado")
elif needle in text:
    p.write_text(text.replace(needle, addition, 1), encoding="utf-8")
    print("OK: configuracion en INSTALLED_APPS")
else:
    raise SystemExit("ERROR: no se encontró ReportesConfig")
PY

python3 manage.py shell -c "from apps.configuracion import models; print('OK: models importan')"
