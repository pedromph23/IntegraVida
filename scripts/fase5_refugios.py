#!/usr/bin/env python3
"""Fase 5 — Refugios. Crea app + modelos + services + admin + tests.
Idempotente. Aborta si la app ya existe (para evitar sobreescribir)."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

APP = BASE / "apps" / "refugios"
if APP.exists():
    sys.exit(f"ERROR: {APP} ya existe. Borra manualmente si quieres regenerar.")

APP.mkdir(parents=True)
(APP / "migrations").mkdir()

def w(rel, content):
    p = APP / rel
    p.write_text(content, encoding="utf-8")
    print(f"  escrito: apps/refugios/{rel}")

# ─── __init__.py ───
w("__init__.py", "")

# ─── apps.py ───
w("apps.py", '''from django.apps import AppConfig


class RefugiosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.refugios"
    verbose_name = "Refugios"
''')

# ─── models.py ───
w("models.py", '''import uuid

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
''')

# ─── services.py ───
w("services.py", '''"""Servicios de refugios — operaciones transaccionales y auditadas."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.refugios.models import Refugio, RegistroOcupacion


@transaction.atomic
def registrar_ocupacion(
    *,
    refugio_id,
    cantidad_nueva,
    fuente=RegistroOcupacion.Fuente.MANUAL,
    notas="",
    usuario,
    request=None,
):
    """
    Registra un cambio de ocupación en un refugio.

    - Bloquea la fila con select_for_update para evitar race conditions (§10).
    - Valida 0 <= cantidad_nueva <= capacidad_total.
    - Crea un RegistroOcupacion (historial inmutable).
    - Audita el cambio con hash encadenado.
    - Si cantidad_nueva == ocupacion_actual, no hace nada (idempotente).
    """
    if cantidad_nueva < 0:
        raise ValidationError(
            {"cantidad_nueva": "La cantidad no puede ser negativa."}
        )

    try:
        refugio = (
            Refugio.objects.select_for_update().get(pk=refugio_id)
        )
    except Refugio.DoesNotExist:
        raise ValidationError({"refugio": "El refugio no existe."})

    if cantidad_nueva > refugio.capacidad_total:
        raise ValidationError(
            {
                "cantidad_nueva": (
                    f"Excede la capacidad total ({refugio.capacidad_total})."
                )
            }
        )

    anterior = refugio.ocupacion_actual
    diferencia = cantidad_nueva - anterior

    if diferencia == 0:
        return refugio

    refugio.ocupacion_actual = cantidad_nueva
    refugio.save(update_fields=["ocupacion_actual", "actualizado_en"])

    RegistroOcupacion.objects.create(
        refugio=refugio,
        cantidad_anterior=anterior,
        cantidad_nueva=cantidad_nueva,
        diferencia=diferencia,
        fuente=fuente,
        notas=notas,
        registrado_por=usuario,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion="refugio.ocupacion_actualizada",
        tipo_objeto="Refugio",
        objeto_id=refugio.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=f"Ocupación: {anterior} → {cantidad_nueva}",
        direccion_ip=ip,
        agente_usuario=user_agent,
        organizacion_id=refugio.organizacion_id,
        metadatos={
            "cantidad_anterior": anterior,
            "cantidad_nueva": cantidad_nueva,
            "diferencia": diferencia,
            "fuente": str(fuente),
        },
    )

    return refugio
''')

# ─── admin.py ───
w("admin.py", '''from django.contrib import admin

from apps.refugios.models import Necesidad, Refugio, RegistroOcupacion


class NecesidadInline(admin.TabularInline):
    model = Necesidad
    extra = 0
    fields = (
        "categoria",
        "descripcion",
        "prioridad",
        "cantidad_estimada",
        "cubierta",
    )


class RegistroOcupacionInline(admin.TabularInline):
    model = RegistroOcupacion
    extra = 0
    can_delete = False
    fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "notas",
        "registrado_por",
        "creado_en",
    )
    readonly_fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Refugio)
class RefugioAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "organizacion",
        "estado_operativo",
        "ocupacion_actual",
        "capacidad_total",
        "porcentaje_ocupacion_display",
    )
    list_filter = ("tipo", "estado_operativo", "organizacion")
    search_fields = ("nombre", "codigo", "direccion")
    readonly_fields = (
        "id",
        "creado_en",
        "actualizado_en",
        "capacidad_disponible_display",
        "porcentaje_ocupacion_display",
    )
    inlines = [NecesidadInline, RegistroOcupacionInline]

    @admin.display(description="% ocupación")
    def porcentaje_ocupacion_display(self, obj):
        return f"{obj.porcentaje_ocupacion}%"

    @admin.display(description="Capacidad disponible")
    def capacidad_disponible_display(self, obj):
        return obj.capacidad_disponible


@admin.register(Necesidad)
class NecesidadAdmin(admin.ModelAdmin):
    list_display = (
        "refugio",
        "categoria",
        "prioridad",
        "cubierta",
        "creada_en",
    )
    list_filter = ("categoria", "prioridad", "cubierta")
    search_fields = ("descripcion", "refugio__nombre")
    readonly_fields = ("id", "creada_en", "actualizada_en")


@admin.register(RegistroOcupacion)
class RegistroOcupacionAdmin(admin.ModelAdmin):
    list_display = (
        "refugio",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "creado_en",
    )
    list_filter = ("fuente",)
    search_fields = ("refugio__nombre",)
    readonly_fields = (
        "id",
        "refugio",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
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

# ─── tests.py ───
w("tests.py", '''from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.organizaciones.models import Organizacion
from apps.refugios.models import Necesidad, Refugio, RegistroOcupacion
from apps.refugios.services import registrar_ocupacion

Usuario = get_user_model()


def _crear_org(slug="org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.ONG,
        codigo=slug,
        estado=Organizacion.Estado.ACTIVA,
    )


class RefugioModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _crear_org("r1")
        cls.usuario = Usuario.objects.create_user(username="g1", password="x")

    def test_crear_refugio_valido(self):
        r = Refugio.objects.create(
            codigo="ref-1",
            nombre="Refugio 1",
            organizacion=self.org,
            responsable=self.usuario,
            direccion="Calle 1",
            capacidad_total=100,
            ocupacion_actual=0,
        )
        self.assertEqual(r.capacidad_disponible, 100)
        self.assertEqual(r.porcentaje_ocupacion, 0.0)
        self.assertFalse(r.esta_lleno)

    def test_codigo_unico(self):
        Refugio.objects.create(
            codigo="ref-x",
            nombre="A",
            organizacion=self.org,
            direccion="x",
            capacidad_total=10,
        )
        with self.assertRaises(IntegrityError):
            Refugio.objects.create(
                codigo="ref-x",
                nombre="B",
                organizacion=self.org,
                direccion="y",
                capacidad_total=10,
            )

    def test_porcentaje_ocupacion(self):
        r = Refugio.objects.create(
            codigo="ref-2",
            nombre="B",
            organizacion=self.org,
            direccion="x",
            capacidad_total=50,
            ocupacion_actual=25,
        )
        self.assertEqual(r.porcentaje_ocupacion, 50.0)
        self.assertEqual(r.capacidad_disponible, 25)

    def test_esta_lleno(self):
        r = Refugio.objects.create(
            codigo="ref-3",
            nombre="C",
            organizacion=self.org,
            direccion="x",
            capacidad_total=10,
            ocupacion_actual=10,
        )
        self.assertTrue(r.esta_lleno)
        self.assertEqual(r.capacidad_disponible, 0)


class RegistrarOcupacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _crear_org("r2")
        cls.usuario = Usuario.objects.create_user(username="u2", password="x")
        cls.refugio = Refugio.objects.create(
            codigo="ref-svc",
            nombre="Refugio Svc",
            organizacion=cls.org,
            direccion="x",
            capacidad_total=100,
            ocupacion_actual=10,
        )

    def test_actualiza_ocupacion(self):
        registrar_ocupacion(
            refugio_id=self.refugio.id,
            cantidad_nueva=50,
            fuente=RegistroOcupacion.Fuente.MANUAL,
            notas="",
            usuario=self.usuario,
        )
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.ocupacion_actual, 50)

    def test_crea_registro_historial(self):
        registrar_ocupacion(
            refugio_id=self.refugio.id,
            cantidad_nueva=50,
            notas="test",
            usuario=self.usuario,
        )
        self.assertEqual(RegistroOcupacion.objects.count(), 1)
        r = RegistroOcupacion.objects.first()
        self.assertEqual(r.cantidad_anterior, 10)
        self.assertEqual(r.cantidad_nueva, 50)
        self.assertEqual(r.diferencia, 40)

    def test_audita_cambio(self):
        registrar_ocupacion(
            refugio_id=self.refugio.id,
            cantidad_nueva=50,
            notas="",
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="refugio.ocupacion_actualizada"
            ).count(),
            1,
        )

    def test_rechaza_exceso_capacidad(self):
        with self.assertRaises(ValidationError):
            registrar_ocupacion(
                refugio_id=self.refugio.id,
                cantidad_nueva=200,
                usuario=self.usuario,
            )
        self.refugio.refresh_from_db()
        self.assertEqual(self.refugio.ocupacion_actual, 10)

    def test_rechaza_negativa(self):
        with self.assertRaises(ValidationError):
            registrar_ocupacion(
                refugio_id=self.refugio.id,
                cantidad_nueva=-1,
                usuario=self.usuario,
            )

    def test_idempotente_si_igual(self):
        registrar_ocupacion(
            refugio_id=self.refugio.id,
            cantidad_nueva=10,
            usuario=self.usuario,
        )
        self.assertEqual(RegistroOcupacion.objects.count(), 0)

    def test_refugio_inexistente(self):
        with self.assertRaises(ValidationError):
            registrar_ocupacion(
                refugio_id="00000000-0000-0000-0000-000000000000",
                cantidad_nueva=10,
                usuario=self.usuario,
            )


class NecesidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _crear_org("r3")
        cls.refugio = Refugio.objects.create(
            codigo="ref-n",
            nombre="N",
            organizacion=cls.org,
            direccion="x",
            capacidad_total=10,
        )

    def test_crear_necesidad(self):
        n = Necesidad.objects.create(
            refugio=self.refugio,
            categoria=Necesidad.Categoria.AGUA,
            descripcion="Falta agua",
            prioridad=Necesidad.Prioridad.ALTA,
        )
        self.assertEqual(n.refugio, self.refugio)
        self.assertFalse(n.cubierta)

    def test_multiples_necesidades_por_refugio(self):
        Necesidad.objects.create(
            refugio=self.refugio,
            categoria=Necesidad.Categoria.AGUA,
            descripcion="A",
        )
        Necesidad.objects.create(
            refugio=self.refugio,
            categoria=Necesidad.Categoria.ALIMENTO,
            descripcion="B",
        )
        self.assertEqual(self.refugio.necesidades.count(), 2)
''')

# ─── migrations/__init__.py ───
(APP / "migrations" / "__init__.py").write_text("", encoding="utf-8")
print("  escrito: apps/refugios/migrations/__init__.py")

print("\n✅ App refugios creada. Ahora ejecuta scripts/fase5_run.sh")
