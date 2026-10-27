import uuid

from django.conf import settings
from django.db import models


class Organizacion(models.Model):
    class Tipo(models.TextChoices):
        ORGANISMO_PUBLICO = "ORGANISMO_PUBLICO", "Organismo público"
        HOSPITAL = "HOSPITAL", "Hospital o centro de salud"
        REFUGIO = "REFUGIO", "Refugio"
        ONG = "ONG", "Organización humanitaria"
        CENTRO_ACOPIO = "CENTRO_ACOPIO", "Centro de acopio"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de verificación"
        ACTIVA = "ACTIVA", "Activa"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"
        INACTIVA = "INACTIVA", "Inactiva"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    codigo = models.SlugField(max_length=100, unique=True)
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PENDIENTE
    )
    descripcion = models.TextField(blank=True)
    telefono_publico = models.CharField(max_length=30, blank=True)
    correo_publico = models.EmailField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["tipo", "estado"]),
            models.Index(fields=["estado", "nombre"]),
        ]
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"

    def __str__(self):
        return self.nombre


class Membresia(models.Model):
    class Rol(models.TextChoices):
        ADMIN_ORGANIZACION = "ADMIN_ORGANIZACION", "Administrador de organización"
        COORDINADOR = "COORDINADOR", "Coordinador"
        OPERADOR = "OPERADOR", "Operador"
        SANITARIO = "SANITARIO", "Personal sanitario"
        LOGISTICA = "LOGISTICA", "Logística"
        CONSULTA = "CONSULTA", "Consulta autorizada"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACTIVA = "ACTIVA", "Activa"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"
        REVOCADA = "REVOCADA", "Revocada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="membresias",
    )
    organizacion = models.ForeignKey(
        Organizacion,
        on_delete=models.PROTECT,
        related_name="membresias",
    )
    rol = models.CharField(max_length=25, choices=Rol.choices)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "organizacion"],
                name="uq_membresia_usuario_organizacion",
            )
        ]
        indexes = [
            models.Index(fields=["organizacion", "estado", "rol"]),
            models.Index(fields=["usuario", "estado"]),
        ]
        verbose_name = "membresía"
        verbose_name_plural = "membresías"

    def __str__(self):
        return f"{self.usuario} — {self.organizacion} ({self.rol})"
