import uuid

from django.conf import settings
from django.db import models


class RegistroExportacion(models.Model):
    """Bitácora operativa de cada generación de reporte.

    No es EventoAuditoria: no tiene hash encadenado porque es operativo
    y la verdadera auditoría está en la fuente (cada modelo ya audita
    sus propias acciones).

    Cumple §20: registrar exportaciones sensibles. Ninguno de los
    reportes de 9.1 exporta PII, pero el registro queda preparado.
    """
    class Tipo(models.TextChoices):
        JSON = "JSON", "JSON"
        CSV = "CSV", "CSV"
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"

    class Contenido(models.TextChoices):
        INVENTARIO_CRITICO = "INVENTARIO_CRITICO", "Inventario crítico"
        CAPACIDAD_OPERATIVA = "CAPACIDAD_OPERATIVA", "Capacidad operativa"

    class Resultado(models.TextChoices):
        EXITOSO = "EXITOSO", "Exitoso"
        ERROR = "ERROR", "Error"
        SIN_DATOS = "SIN_DATOS", "Sin datos"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="exportaciones_reportes",
    )
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion", on_delete=models.PROTECT,
        null=True, blank=True, related_name="exportaciones_reportes",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    contenido = models.CharField(
        max_length=30, choices=Contenido.choices, db_index=True,
    )
    parametros = models.JSONField(default=dict, blank=True)
    filas_incluidas = models.PositiveIntegerField(default=0)
    archivo_ruta = models.CharField(max_length=500, blank=True)
    tamano_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    resultado = models.CharField(
        max_length=15, choices=Resultado.choices,
        default=Resultado.EXITOSO, db_index=True,
    )
    detalle = models.CharField(max_length=500, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["usuario", "-creado_en"]),
            models.Index(fields=["contenido", "-creado_en"]),
            models.Index(fields=["organizacion", "-creado_en"]),
        ]
        verbose_name = "registro de exportación"
        verbose_name_plural = "registros de exportación"

    def __str__(self):
        return (
            f"{self.contenido} — {self.usuario} — "
            f"{self.get_resultado_display()}"
        )
