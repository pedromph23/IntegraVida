#!/usr/bin/env python3
"""Fase 6.2 — Pacientes, Episodios, Contactos de emergencia."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

APP = BASE / "apps" / "pacientes"
if APP.exists():
    sys.exit(f"ERROR: {APP} ya existe. Bórralo para regenerar.")

APP.mkdir(parents=True)
(APP / "migrations").mkdir()
(APP / "migrations" / "__init__.py").write_text("", encoding="utf-8")

def w(rel, content):
    (APP / rel).write_text(content, encoding="utf-8")
    print(f"  escrito: apps/pacientes/{rel}")

w("__init__.py", "")

w("apps.py", '''from django.apps import AppConfig


class PacientesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pacientes"
    verbose_name = "Pacientes"
''')

w("models.py", '''import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Paciente(models.Model):
    class SexoBiologico(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"
        INTERSEX = "I", "Intersexual"
        NO_ESPECIFICADO = "N", "No especificado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identificación (cedula_hash calculado en services.py)
    cedula = models.CharField(max_length=20, blank=True, default="")
    cedula_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="HMAC-SHA256 de la cédula normalizada. Calculado automáticamente.",
    )

    # Datos personales
    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo_biologico = models.CharField(
        max_length=1,
        choices=SexoBiologico.choices,
        default=SexoBiologico.NO_ESPECIFICADO,
    )

    # Contacto (opcional, puede existir sin paciente identificar)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    # Cuenta vinculada (opcional, para futura consulta del titular)
    cuenta_vinculada = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes_vinculados",
    )

    notas_internas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["apellidos", "nombres"]),
            models.Index(fields=["-creado_en"]),
        ]
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - (
                (hoy.month, hoy.day)
                < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        )


class ContactoEmergencia(models.Model):
    class Parentesco(models.TextChoices):
        PADRE = "PADRE", "Padre"
        MADRE = "MADRE", "Madre"
        HIJO = "HIJO", "Hijo/a"
        CONYUGE = "CONYUGE", "Cónyuge / Pareja"
        HERMANO = "HERMANO", "Hermano/a"
        TUTOR = "TUTOR", "Tutor legal"
        AMIGO = "AMIGO", "Amigo/a"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, related_name="contactos"
    )
    nombre = models.CharField(max_length=200)
    parentesco = models.CharField(max_length=20, choices=Parentesco.choices)
    telefono = models.CharField(max_length=30)
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-es_principal", "-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(es_principal=True),
                name="un_contacto_principal_por_paciente",
            ),
        ]
        indexes = [
            models.Index(fields=["paciente", "-es_principal"]),
        ]
        verbose_name = "contacto de emergencia"
        verbose_name_plural = "contactos de emergencia"

    def __str__(self):
        return f"{self.nombre} ({self.get_parentesco_display()})"


class Episodio(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EN_ATENCION = "EN_ATENCION", "En atención"
        DERIVADO = "DERIVADO", "Derivado"
        CERRADO = "CERRADO", "Cerrado"
        FALLECIDO = "FALLECIDO", "Fallecido"
        ABANDONO = "ABANDONO", "Abandono"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, related_name="episodios"
    )
    hospital = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="episodios",
    )
    refugio = models.ForeignKey(
        "refugios.Refugio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="episodios",
    )
    motivo_consulta = models.TextField()
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.ABIERTO,
        db_index=True,
    )
    fecha_ingreso = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_egreso = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="episodios_registrados",
    )
    notas_internas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_ingreso"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(hospital_id__isnull=False, refugio_id__isnull=True)
                    | models.Q(hospital_id__isnull=True, refugio_id__isnull=False)
                ),
                name="episodio_uno_y_solo_un_centro",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(fecha_egreso__isnull=True)
                    | models.Q(fecha_egreso__gte=models.F("fecha_ingreso"))
                ),
                name="episodio_egreso_posterior_a_ingreso",
            ),
        ]
        indexes = [
            models.Index(fields=["paciente", "-fecha_ingreso"]),
            models.Index(fields=["hospital", "estado"]),
            models.Index(fields=["refugio", "estado"]),
        ]
        verbose_name = "episodio"
        verbose_name_plural = "episodios"

    def __str__(self):
        centro = self.hospital or self.refugio
        return f"{self.paciente} — {centro} ({self.get_estado_display()})"
''')

w("services.py", '''"""Servicios de pacientes — normalización, hash y creación controlada."""

import hashlib
import hmac
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.pacientes.models import Paciente


def _hmac_key():
    """
    Clave HMAC para `cedula_hash`.

    Prioridad:
    1. PACIENTE_CEDULA_HMAC_KEY (independiente, para producción)
    2. Derivada de SECRET_KEY (desarrollo, migrable)

    En Fase 11 se migrará a variable independiente y se documentará
    la rotación.
    """
    raw = getattr(settings, "PACIENTE_CEDULA_HMAC_KEY", None) or settings.SECRET_KEY
    return hashlib.sha256(f"integravida:cedula:{raw}".encode("utf-8")).digest()


def normalizar_cedula(cedula):
    """Normaliza a mayúsculas alfanuméricas: 'V-12.345.678' -> 'V12345678'."""
    if not cedula:
        return ""
    return "".join(c for c in str(cedula).upper() if c.isalnum())


def calcular_cedula_hash(cedula):
    """Calcula HMAC-SHA256 de la cédula normalizada."""
    normalizada = normalizar_cedula(cedula)
    if not normalizada:
        return None
    return hmac.new(
        _hmac_key(), normalizada.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@transaction.atomic
def crear_paciente(
    *,
    cedula="",
    nombres,
    apellidos,
    fecha_nacimiento=None,
    sexo_biologico=Paciente.SexoBiologico.NO_ESPECIFICADO,
    telefono="",
    email="",
    cuenta_vinculada=None,
    notas_internas="",
    usuario,
    request=None,
):
    """
    Crea un paciente calculando automáticamente su `cedula_hash`.

    - Si la cédula está vacía, `cedula_hash` queda NULL.
    - Si la cédula ya existe (mismo hash), lanza ValidationError.
    - Audita la creación con hash encadenado.
    """
    nombres = (nombres or "").strip()
    apellidos = (apellidos or "").strip()

    if not nombres:
        raise ValidationError({"nombres": "Los nombres son obligatorios."})
    if not apellidos:
        raise ValidationError({"apellidos": "Los apellidos son obligatorios."})

    cedula_hash = calcular_cedula_hash(cedula)

    if cedula_hash and Paciente.objects.filter(cedula_hash=cedula_hash).exists():
        raise ValidationError(
            {"cedula": "Ya existe un paciente registrado con esta cédula."}
        )

    paciente = Paciente.objects.create(
        cedula=(cedula or "").strip(),
        cedula_hash=cedula_hash,
        nombres=nombres,
        apellidos=apellidos,
        fecha_nacimiento=fecha_nacimiento,
        sexo_biologico=sexo_biologico,
        telefono=(telefono or "").strip(),
        email=(email or "").strip(),
        cuenta_vinculada=cuenta_vinculada,
        notas_internas=notas_internas,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="paciente.creado",
        tipo_objeto="Paciente",
        objeto_id=paciente.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion="Creación de expediente de paciente.",
        direccion_ip=ip,
        agente_usuario=user_agent,
        metadatos={
            "tiene_cedula": bool(cedula_hash),
            "sexo_biologico": paciente.sexo_biologico,
        },
    )

    return paciente


def buscar_paciente_por_cedula(cedula):
    """Busca un paciente por cédula normalizada. Devuelve None si no existe."""
    hash_busqueda = calcular_cedula_hash(cedula)
    if not hash_busqueda:
        return None
    return Paciente.objects.filter(cedula_hash=hash_busqueda).first()
''')

w("admin.py", '''from django.contrib import admin

from apps.pacientes.models import ContactoEmergencia, Episodio, Paciente


class ContactoEmergenciaInline(admin.TabularInline):
    model = ContactoEmergencia
    extra = 0
    fields = ("nombre", "parentesco", "telefono", "es_principal")


class EpisodioInline(admin.TabularInline):
    model = Episodio
    extra = 0
    fields = (
        "hospital",
        "refugio",
        "motivo_consulta",
        "estado",
        "fecha_ingreso",
        "fecha_egreso",
    )
    readonly_fields = ("fecha_ingreso",)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        "apellidos",
        "nombres",
        "cedula",
        "edad",
        "sexo_biologico",
        "creado_en",
    )
    search_fields = (
        "apellidos",
        "nombres",
        "cedula",
        "cedula_hash",
    )
    list_filter = ("sexo_biologico",)
    readonly_fields = ("id", "cedula_hash", "creado_en", "actualizado_en")
    inlines = [ContactoEmergenciaInline, EpisodioInline]

    @admin.display(description="Edad")
    def edad(self, obj):
        return obj.edad or "—"


@admin.register(ContactoEmergencia)
class ContactoEmergenciaAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "nombre",
        "parentesco",
        "telefono",
        "es_principal",
    )
    list_filter = ("parentesco", "es_principal")
    search_fields = ("nombre", "paciente__apellidos")


@admin.register(Episodio)
class EpisodioAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "hospital",
        "refugio",
        "estado",
        "fecha_ingreso",
        "fecha_egreso",
    )
    list_filter = ("estado",)
    search_fields = ("paciente__apellidos", "paciente__nombres")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    date_hierarchy = "fecha_ingreso"
''')

print("\n✅ App pacientes creada.")
