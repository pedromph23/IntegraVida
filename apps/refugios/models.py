import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Refugio(models.Model):
    class Tipo(models.TextChoices):
        REFUGIO = "REFUGIO", "Refugio"
        CENTRO_ACOPIO = "CENTRO_ACOPIO", "Centro de acopio"
        ALBERGUE_TEMPORAL = "ALBERGUE_TEMPORAL", "Albergue temporal"
        OTRO = "OTRO", "Otro"

    class EstadoOperativo(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        LLENO = "LLENO", "Lleno"
        MANTENIMIENTO = "MANTENIMIENTO", "En mantenimiento"
        CERRADO = "CERRADO", "Cerrado"
        INACTIVO = "INACTIVO", "Inactivo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=100, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(
        max_length=25, choices=Tipo.choices, default=Tipo.REFUGIO
    )
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="refugios",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refugios_a_cargo",
    )
    ubicacion = gis_models.PointField(
        srid=4326, geography=True, null=True, blank=True
    )
    direccion = models.CharField(max_length=300)
    referencia_lugar = models.CharField(max_length=250, blank=True)
    municipio = models.ForeignKey(
        "territorio.Municipio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refugios",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refugios",
    )
    capacidad_total = models.PositiveIntegerField(default=0)
    ocupacion_actual = models.PositiveIntegerField(default=0)
    servicios = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de servicios disponibles (catálogo libre por ahora)",
    )
    estado_operativo = models.CharField(
        max_length=20,
        choices=EstadoOperativo.choices,
        default=EstadoOperativo.ACTIVO,
        db_index=True,
    )
    telefono_publico = models.CharField(max_length=30, blank=True)
    correo_publico = models.EmailField(blank=True)
    notas_internas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    ocupacion_actual__lte=models.F("capacidad_total")
                ),
                name="refugio_ocupacion_lte_capacidad",
            ),
        ]
        indexes = [
            models.Index(fields=["estado_operativo", "organizacion"]),
            models.Index(fields=["organizacion", "estado_operativo"]),
            models.Index(fields=["municipio", "parroquia"]),
        ]
        verbose_name = "refugio"
        verbose_name_plural = "refugios"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def capacidad_disponible(self):
        return max(0, self.capacidad_total - self.ocupacion_actual)

    @property
    def porcentaje_ocupacion(self):
        if not self.capacidad_total:
            return 0.0
        return round((self.ocupacion_actual / self.capacidad_total) * 100, 1)

    @property
    def esta_lleno(self):
        return self.ocupacion_actual >= self.capacidad_total

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None


class Necesidad(models.Model):
    class Categoria(models.TextChoices):
        AGUA = "AGUA", "Agua"
        ALIMENTO = "ALIMENTO", "Alimento"
        MEDICINA = "MEDICINA", "Medicina"
        ABRIGO = "ABRIGO", "Abrigo"
        HIGIENE = "HIGIENE", "Higiene"
        ROPA = "ROPA", "Ropa"
        OTRO = "OTRO", "Otro"

    class Prioridad(models.IntegerChoices):
        BAJA = 1, "Baja"
        MEDIA = 2, "Media"
        ALTA = 3, "Alta"
        CRITICA = 4, "Crítica"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refugio = models.ForeignKey(
        Refugio, on_delete=models.PROTECT, related_name="necesidades"
    )
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    descripcion = models.TextField()
    prioridad = models.PositiveSmallIntegerField(
        choices=Prioridad.choices, default=Prioridad.MEDIA
    )
    cantidad_estimada = models.CharField(max_length=100, blank=True)
    cubierta = models.BooleanField(default=False, db_index=True)
    cubierta_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-prioridad", "-creada_en"]
        indexes = [
            models.Index(fields=["refugio", "cubierta"]),
            models.Index(fields=["cubierta", "prioridad"]),
        ]
        verbose_name = "necesidad"
        verbose_name_plural = "necesidades"

    def __str__(self):
        return f"{self.get_categoria_display()} — {self.refugio.nombre}"


class RegistroOcupacion(models.Model):
    class Fuente(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        IMPORTACION = "IMPORTACION", "Importación"
        AJUSTE = "AJUSTE", "Ajuste"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refugio = models.ForeignKey(
        Refugio, on_delete=models.PROTECT, related_name="registros_ocupacion"
    )
    cantidad_anterior = models.PositiveIntegerField()
    cantidad_nueva = models.PositiveIntegerField()
    diferencia = models.IntegerField()
    fuente = models.CharField(
        max_length=15, choices=Fuente.choices, default=Fuente.MANUAL
    )
    notas = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registros_ocupacion",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["refugio", "-creado_en"])]
        verbose_name = "registro de ocupación"
        verbose_name_plural = "registros de ocupación"

    def __str__(self):
        return (
            f"{self.refugio.nombre}: "
            f"{self.cantidad_anterior} → {self.cantidad_nueva}"
        )
