#!/usr/bin/env python3
"""Fase 6.1 — Hospitales, Servicios y Recursos."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

APP = BASE / "apps" / "hospitales"
if APP.exists():
    sys.exit(f"ERROR: {APP} ya existe. Bórralo para regenerar.")

APP.mkdir(parents=True)
(APP / "migrations").mkdir()

def w(rel, content):
    p = APP / rel
    p.write_text(content, encoding="utf-8")
    print(f"  escrito: apps/hospitales/{rel}")

w("__init__.py", "")
(APP / "migrations" / "__init__.py").write_text("", encoding="utf-8")

w("apps.py", '''from django.apps import AppConfig


class HospitalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.hospitales"
    verbose_name = "Hospitales"
''')

w("models.py", '''import uuid

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
''')

w("services.py", '''"""Servicios de hospitales — operaciones transaccionales y auditadas."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.hospitales.models import RecursoHospitalario, RegistroDisponibilidad


@transaction.atomic
def registrar_disponibilidad(
    *,
    recurso_id,
    cantidad_nueva,
    usuario,
    notas="",
    request=None,
):
    """
    Registra un cambio de disponibilidad en un recurso hospitalario.

    - select_for_update para concurrencia (§10).
    - Valida 0 <= cantidad_nueva <= capacidad_total.
    - Crea un RegistroDisponibilidad (historial inmutable).
    - Audita con hash encadenado.
    - Idempotente si cantidad_nueva == disponible.
    """
    if cantidad_nueva < 0:
        raise ValidationError(
            {"cantidad_nueva": "La cantidad no puede ser negativa."}
        )

    try:
        recurso = (
            RecursoHospitalario.objects
            .select_for_update()
            .select_related("hospital")
            .get(pk=recurso_id)
        )
    except RecursoHospitalario.DoesNotExist:
        raise ValidationError({"recurso": "El recurso no existe."})

    if recurso.capacidad_total == 0:
        raise ValidationError(
            {"recurso": "El recurso no tiene capacidad total definida."}
        )

    if cantidad_nueva > recurso.capacidad_total:
        raise ValidationError(
            {
                "cantidad_nueva": (
                    f"Excede la capacidad total ({recurso.capacidad_total})."
                )
            }
        )

    anterior = recurso.disponible
    diferencia = cantidad_nueva - anterior

    if diferencia == 0:
        return recurso

    recurso.disponible = cantidad_nueva
    recurso.save(update_fields=["disponible", "actualizado_en"])

    RegistroDisponibilidad.objects.create(
        recurso=recurso,
        cantidad_anterior=anterior,
        cantidad_nueva=cantidad_nueva,
        diferencia=diferencia,
        registrado_por=usuario,
        notas=notas,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="hospital.disponibilidad_actualizada",
        tipo_objeto="RecursoHospitalario",
        objeto_id=recurso.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Disponibilidad de {recurso.get_tipo_display()}: "
            f"{anterior} -> {cantidad_nueva}"
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=recurso.hospital.organizacion_id,
        metadatos={
            "tipo": recurso.tipo,
            "cantidad_anterior": anterior,
            "cantidad_nueva": cantidad_nueva,
            "diferencia": diferencia,
        },
    )

    return recurso
''')

w("admin.py", '''from django.contrib import admin

from apps.hospitales.models import (
    Hospital,
    HospitalServicio,
    RecursoHospitalario,
    RegistroDisponibilidad,
    Servicio,
)


class HospitalServicioInline(admin.TabularInline):
    model = HospitalServicio
    extra = 0
    autocomplete_fields = ("servicio",)
    fields = ("servicio", "disponible", "notas", "actualizado_en")
    readonly_fields = ("actualizado_en",)


class RecursoHospitalarioInline(admin.TabularInline):
    model = RecursoHospitalario
    extra = 0
    fields = ("tipo", "capacidad_total", "disponible", "actualizado_en")
    readonly_fields = ("actualizado_en",)


class RegistroDisponibilidadInline(admin.TabularInline):
    model = RegistroDisponibilidad
    extra = 0
    can_delete = False
    fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "notas",
        "registrado_por",
        "creado_en",
    )
    readonly_fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "nivel",
        "estado_operativo",
        "organizacion",
    )
    list_filter = ("tipo", "nivel", "estado_operativo", "organizacion")
    search_fields = ("nombre", "codigo", "direccion")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    inlines = [HospitalServicioInline, RecursoHospitalarioInline]


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre", "codigo")
    readonly_fields = ("id",)


@admin.register(RecursoHospitalario)
class RecursoHospitalarioAdmin(admin.ModelAdmin):
    list_display = (
        "hospital",
        "tipo",
        "capacidad_total",
        "disponible",
        "ocupados",
        "actualizado_en",
    )
    list_filter = ("tipo",)
    search_fields = ("hospital__nombre", "hospital__codigo")
    readonly_fields = ("id", "actualizado_en", "ocupados")
    inlines = [RegistroDisponibilidadInline]


@admin.register(RegistroDisponibilidad)
class RegistroDisponibilidadAdmin(admin.ModelAdmin):
    list_display = (
        "recurso",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "registrado_por",
        "creado_en",
    )
    search_fields = ("recurso__hospital__nombre",)
    readonly_fields = (
        "id",
        "recurso",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
''')

print("\n✅ App hospitales creada. Ejecuta fase6_1_tests_docs.py después de makemigrations.")
