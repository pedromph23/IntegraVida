import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Emergencia(models.Model):
    class Categoria(models.TextChoices):
        INUNDACION = "INUNDACION", "Inundación"
        INCENDIO = "INCENDIO", "Incendio"
        ACCIDENTE = "ACCIDENTE", "Accidente"
        DESLIZAMIENTO = "DESLIZAMIENTO", "Deslizamiento"
        ESTRUCTURAL = "ESTRUCTURAL", "Daño estructural"
        MEDICA = "MEDICA", "Emergencia médica"
        VIAS = "VIAS", "Problema en vía"
        VIOLENCIA = "VIOLENCIA", "Situación de violencia"
        SERVICIOS = "SERVICIOS", "Falla de servicios básicos"
        OTRA = "OTRA", "Otra emergencia"

    class Gravedad(models.IntegerChoices):
        BAJA = 1, "Baja"
        MODERADA = 2, "Moderada"
        ALTA = 3, "Alta"
        CRITICA = 4, "Crítica"

    class Estado(models.TextChoices):
        RECIBIDA = "RECIBIDA", "Recibida"
        EN_VERIFICACION = "EN_VERIFICACION", "En verificación"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        EN_ATENCION = "EN_ATENCION", "En atención"
        RESUELTA = "RESUELTA", "Resuelta"
        DESCARTADA = "DESCARTADA", "Descartada"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField()
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        db_index=True,
    )
    gravedad = models.PositiveSmallIntegerField(
        choices=Gravedad.choices,
        default=Gravedad.MODERADA,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(4),
        ],
        db_index=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.RECIBIDA,
        db_index=True,
    )

    ubicacion_texto = models.CharField(max_length=300)
    referencia_lugar = models.CharField(max_length=250, blank=True)
    punto = gis_models.PointField(
        srid=4326,
        geography=True,
        null=True,
        blank=True,
    )

    municipio = models.ForeignKey(
        "territorio.Municipio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergencias",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergencias",
    )

    reportada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergencias_reportadas",
    )
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergencias",
    )

    ocurrida_en = models.DateTimeField(
        null=True,
        blank=True,
    )
    creada_en = models.DateTimeField(default=timezone.now, db_index=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada_en"]
        indexes = [
            models.Index(
                fields=["estado", "gravedad"],
                name="emerg_estado_grav_idx",
            ),
            models.Index(
                fields=["categoria", "creada_en"],
                name="emerg_cat_fecha_idx",
            ),
        ]
        verbose_name = "emergencia"
        verbose_name_plural = "emergencias"

    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()})"


class ReporteEmergencia(models.Model):
    class EstadoRevision(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de revisión"
        EN_REVISION = "EN_REVISION", "En revisión"
        VINCULADO = "VINCULADO", "Vinculado a una emergencia"
        DUPLICADO = "DUPLICADO", "Reporte duplicado"
        DESCARTADO = "DESCARTADO", "Descartado"

    class Canal(models.TextChoices):
        WEB = "WEB", "Portal web"
        TELEFONO = "TELEFONO", "Teléfono"
        ORGANIZACION = "ORGANIZACION", "Organización"
        INTERNO = "INTERNO", "Registro interno"
        OTRO = "OTRO", "Otro canal"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    emergencia = models.ForeignKey(
        Emergencia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes",
    )
    reportante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_emergencias",
    )

    categoria = models.CharField(
        max_length=20,
        choices=Emergencia.Categoria.choices,
        default=Emergencia.Categoria.OTRA,
        db_index=True,
    )
    descripcion = models.TextField()
    ubicacion_texto = models.CharField(max_length=300)
    referencia_lugar = models.CharField(max_length=250, blank=True)
    punto = gis_models.PointField(
        srid=4326,
        geography=True,
        null=True,
        blank=True,
    )

    municipio = models.ForeignKey(
        "territorio.Municipio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_emergencias",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_emergencias",
    )

    canal = models.CharField(
        max_length=15,
        choices=Canal.choices,
        default=Canal.WEB,
    )
    estado_revision = models.CharField(
        max_length=15,
        choices=EstadoRevision.choices,
        default=EstadoRevision.PENDIENTE,
        db_index=True,
    )
    recibido_en = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recibido_en"]
        indexes = [
            models.Index(
                fields=["estado_revision", "recibido_en"],
                name="reporte_estado_fecha_idx",
            ),
        ]
        verbose_name = "reporte de emergencia"
        verbose_name_plural = "reportes de emergencia"

    def __str__(self):
        return f"Reporte {self.pk} ({self.get_estado_revision_display()})"