import uuid

from django.contrib.gis.db import models


class EntidadFederal(models.Model):
    class Tipo(models.TextChoices):
        ESTADO = "ESTADO", "Estado"
        DISTRITO_CAPITAL = "DISTRITO_CAPITAL", "Distrito Capital"
        DEPENDENCIA_FEDERAL = "DEPENDENCIA_FEDERAL", "Dependencia federal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    geometria = models.MultiPolygonField(
        srid=4326, null=True, blank=True
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "entidad federal"
        verbose_name_plural = "entidades federales"
        indexes = [
            models.Index(fields=["tipo", "activa"]),
            models.Index(fields=["nombre"]),
        ]

    def __str__(self):
        return self.nombre


class Municipio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entidad_federal = models.ForeignKey(
        EntidadFederal,
        on_delete=models.PROTECT,
        related_name="municipios",
    )
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=30)
    geometria = models.MultiPolygonField(
        srid=4326, null=True, blank=True
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["entidad_federal__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["entidad_federal", "codigo"],
                name="uq_municipio_entidad_codigo",
            ),
        ]
        indexes = [
            models.Index(fields=["entidad_federal", "activo"]),
            models.Index(fields=["nombre"]),
        ]
        verbose_name = "municipio"
        verbose_name_plural = "municipios"

    def __str__(self):
        return f"{self.nombre} — {self.entidad_federal.nombre}"


class Parroquia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name="parroquias",
    )
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=30)
    geometria = models.MultiPolygonField(
        srid=4326, null=True, blank=True
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["municipio__entidad_federal__nombre", "municipio__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "codigo"],
                name="uq_parroquia_municipio_codigo",
            ),
        ]
        indexes = [
            models.Index(fields=["municipio", "activa"]),
            models.Index(fields=["nombre"]),
        ]
        verbose_name = "parroquia"
        verbose_name_plural = "parroquias"

    def __str__(self):
        return f"{self.nombre} — {self.municipio.nombre}"
