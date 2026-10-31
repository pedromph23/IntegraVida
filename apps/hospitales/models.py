import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Hospital(models.Model):
    class Tipo(models.TextChoices):
        HOSPITAL = "HOSPITAL", "Hospital"
        CLINICA = "CLINICA", "Clínica"
        CENTRO_SALUD = "CENTRO_SALUD", "Centro de salud"
        AMBULATORIO = "AMBULATORIO", "Ambulatorio"

    class Nivel(models.TextChoices):
        NIVEL_I = "NIVEL_I", "Nivel I"
        NIVEL_II = "NIVEL_II", "Nivel II"
        NIVEL_III = "NIVEL_III", "Nivel III"
        NIVEL_IV = "NIVEL_IV", "Nivel IV"

    class EstadoOperativo(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        SATURADO = "SATURADO", "Saturado"
        COLAPSADO = "COLAPSADO", "Colapsado"
        NO_OPERATIVO = "NO_OPERATIVO", "No operativo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=100, unique=True)
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(
        max_length=20, choices=Tipo.choices, default=Tipo.HOSPITAL
    )
    nivel = models.CharField(max_length=15, choices=Nivel.choices)
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="hospitales",
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hospitales_a_cargo",
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
        related_name="hospitales",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hospitales",
    )
    telefono_publico = models.CharField(max_length=30, blank=True)
    correo_publico = models.EmailField(blank=True)
    notas_internas = models.TextField(blank=True)
    estado_operativo = models.CharField(
        max_length=20,
        choices=EstadoOperativo.choices,
        default=EstadoOperativo.DISPONIBLE,
        db_index=True,
    )
    servicios = models.ManyToManyField(
        "Servicio",
        through="HospitalServicio",
        related_name="hospitales",
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado_operativo", "organizacion"]),
            models.Index(fields=["organizacion", "estado_operativo"]),
            models.Index(fields=["tipo", "nivel"]),
            models.Index(fields=["municipio", "parroquia"]),
        ]
        verbose_name = "hospital"
        verbose_name_plural = "hospitales"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None


class Servicio(models.Model):
    class Tipo(models.TextChoices):
        SERVICIO = "SERVICIO", "Servicio"
        ESPECIALIDAD = "ESPECIALIDAD", "Especialidad"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(
        max_length=15, choices=Tipo.choices, default=Tipo.SERVICIO
    )
    activo = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "servicio"
        verbose_name_plural = "servicios"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class HospitalServicio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT, related_name="servicios_through"
    )
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="hospitales_through"
    )
    disponible = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "servicio"],
                name="unique_hospital_servicio",
            )
        ]
        indexes = [
            models.Index(fields=["servicio", "disponible"]),
        ]
        verbose_name = "servicio del hospital"
        verbose_name_plural = "servicios del hospital"

    def __str__(self):
        return f"{self.hospital.codigo} — {self.servicio.codigo}"


class RecursoHospitalario(models.Model):
    class Tipo(models.TextChoices):
        UCI = "UCI", "Unidad de Cuidados Intensivos"
        URGENCIA = "URGENCIA", "Urgencias"
        QUIROFANO = "QUIROFANO", "Quirófano"
        HOSPITALIZACION = "HOSPITALIZACION", "Hospitalización"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT, related_name="recursos"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    capacidad_total = models.PositiveIntegerField(default=0)
    disponible = models.PositiveIntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hospital", "tipo"]
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "tipo"],
                name="unique_hospital_tipo_recurso",
            ),
            models.CheckConstraint(
                condition=models.Q(disponible__lte=models.F("capacidad_total")),
                name="recurso_disponible_lte_capacidad",
            ),
        ]
        indexes = [
            models.Index(fields=["hospital", "tipo"]),
        ]
        verbose_name = "recurso hospitalario"
        verbose_name_plural = "recursos hospitalarios"

    def __str__(self):
        return (
            f"{self.hospital.codigo} — {self.get_tipo_display()}: "
            f"{self.disponible}/{self.capacidad_total}"
        )

    @property
    def ocupados(self):
        return max(0, self.capacidad_total - self.disponible)


class RegistroDisponibilidad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recurso = models.ForeignKey(
        RecursoHospitalario,
        on_delete=models.PROTECT,
        related_name="registros",
    )
    cantidad_anterior = models.PositiveIntegerField()
    cantidad_nueva = models.PositiveIntegerField()
    diferencia = models.IntegerField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registros_disponibilidad",
    )
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["recurso", "-creado_en"]),
        ]
        verbose_name = "registro de disponibilidad"
        verbose_name_plural = "registros de disponibilidad"

    def __str__(self):
        return (
            f"{self.recurso}: {self.cantidad_anterior} → {self.cantidad_nueva}"
        )
