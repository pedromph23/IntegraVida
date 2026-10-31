import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Insumo(models.Model):
    class Categoria(models.TextChoices):
        AGUA = "AGUA", "Agua"
        ALIMENTO = "ALIMENTO", "Alimento"
        MEDICINA = "MEDICINA", "Medicina"
        HIGIENE = "HIGIENE", "Higiene"
        ABRIGO = "ABRIGO", "Abrigo"
        ROPA = "ROPA", "Ropa"
        EQUIPO_MEDICO = "EQUIPO_MEDICO", "Equipo médico"
        OTRO = "OTRO", "Otro"

    class UnidadMedida(models.TextChoices):
        UNIDAD = "UNIDAD", "Unidad"
        GRAMO = "GRAMO", "Gramo"
        KILOGRAMO = "KILOGRAMO", "Kilogramo"
        MILILITRO = "MILILITRO", "Mililitro"
        LITRO = "LITRO", "Litro"
        CAJA = "CAJA", "Caja"
        PAQUETE = "PAQUETE", "Paquete"
        RACION = "RACION", "Ración"
        FRASCO = "FRASCO", "Frasco"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices, db_index=True
    )
    subcategoria = models.CharField(max_length=80, blank=True)
    unidad_medida = models.CharField(
        max_length=15, choices=UnidadMedida.choices
    )
    requiere_lote = models.BooleanField(default=False)
    requiere_vencimiento = models.BooleanField(default=False)
    vida_util_dias = models.PositiveIntegerField(null=True, blank=True)
    stock_minimo_global = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "nombre"]
        indexes = [
            models.Index(fields=["categoria", "activo"]),
            models.Index(fields=["nombre"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(requiere_vencimiento=False)
                    | models.Q(requiere_lote=True)
                ),
                name="insumo_vencimiento_requiere_lote",
            ),
        ]
        verbose_name = "insumo"
        verbose_name_plural = "insumos"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Almacen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=200)
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="almacenes",
    )
    hospital = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    refugio = models.ForeignKey(
        "refugios.Refugio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    ubicacion = gis_models.PointField(
        srid=4326, geography=True, null=True, blank=True
    )
    direccion = models.CharField(max_length=300, blank=True)
    municipio = models.ForeignKey(
        "territorio.Municipio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["organizacion", "activo"]),
            models.Index(fields=["hospital", "activo"]),
            models.Index(fields=["refugio", "activo"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~(
                    models.Q(hospital__isnull=False)
                    & models.Q(refugio__isnull=False)
                ),
                name="almacen_no_ambos_hospital_y_refugio",
            ),
        ]
        verbose_name = "almacén"
        verbose_name_plural = "almacenes"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def tipo_ubicacion(self):
        if self.hospital_id:
            return "HOSPITAL"
        if self.refugio_id:
            return "REFUGIO"
        return "INDEPENDIENTE"

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None
