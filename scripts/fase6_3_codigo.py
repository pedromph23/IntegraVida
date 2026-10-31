#!/usr/bin/env python3
"""Fase 6.3 — Ámbito de Membresía + App Triaje."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def patch(rel, old, new, label=""):
    p = BASE / rel
    if not p.exists():
        sys.exit(f"ERROR: no existe {rel}")
    text = p.read_text(encoding="utf-8")
    if old not in text and new in text:
        print(f"  ya aplicado: {label}")
        return
    if text.count(old) != 1:
        sys.exit(f"ERROR: {rel} — patrón aparece {text.count(old)} veces")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label}")

def w(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  escrito: {rel}")

# ══════════════════════════════════════════════════════════════════
# 1) organizaciones/models.py — ambito_municipio en Membresia
# ══════════════════════════════════════════════════════════════════
print("== 1/4 Membresia.ambito_municipio ==")
patch(
    "apps/organizaciones/models.py",
    "    rol = models.CharField(max_length=25, choices=Rol.choices)\n"
    "    estado = models.CharField(\n"
    "        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE\n"
    "    )\n",
    "    rol = models.CharField(max_length=25, choices=Rol.choices)\n"
    "    estado = models.CharField(\n"
    "        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE\n"
    "    )\n"
    "    ambito_municipio = models.ForeignKey(\n"
    "        \"territorio.Municipio\",\n"
    "        on_delete=models.PROTECT,\n"
    "        null=True,\n"
    "        blank=True,\n"
    "        related_name=\"membresias_restringidas\",\n"
    "        help_text=(\n"
    "            \"Si está definido, la membresía solo accede a recursos \"\n"
    "            \"ubicados en este municipio. NULL = sin restricción \"\n"
    "            \"geográfica dentro de la organización.\"\n"
    "        ),\n"
    "    )\n",
    "Membresia.ambito_municipio añadido"
)

# ══════════════════════════════════════════════════════════════════
# 2) pacientes/services.py — filtrar_episodios_por_ambito
# ══════════════════════════════════════════════════════════════════
print("== 2/4 pacientes/services.py: filtro de ámbito ==")
svc_path = BASE / "apps" / "pacientes" / "services.py"
text = svc_path.read_text(encoding="utf-8")

nuevo_bloque = '''

def filtrar_episodios_por_ambito(queryset, usuario):
    """
    Filtra un queryset de Episodios según el ámbito de las membresías del usuario.

    Reglas (§8, §11):
    - Superusuario: ve todos los episodios.
    - Membresía ACTIVA con ambito_municipio NULL: ve todos los episodios de
      su organización.
    - Membresía ACTIVA con ambito_municipio definido: ve solo los episodios
      cuyo hospital o refugio esté en ese municipio.
    - Sin membresía: no ve nada.

    Se combinan con OR: un usuario con múltiples membresías ve la unión.
    """
    from django.db.models import Q

    from apps.organizaciones.models import Membresia
    from apps.organizaciones.services import puede_administrar_plataforma

    if puede_administrar_plataforma(usuario):
        return queryset

    if not getattr(usuario, "is_authenticated", False):
        return queryset.none()

    membresias = Membresia.objects.filter(
        usuario=usuario,
        estado=Membresia.Estado.ACTIVA,
    ).values_list("organizacion_id", "ambito_municipio_id")

    orgs_sin_restriccion = []
    municipios_restringidos = []

    for org_id, municipio_id in membresias:
        if municipio_id is None:
            orgs_sin_restriccion.append(org_id)
        else:
            municipios_restringidos.append(municipio_id)

    if not orgs_sin_restriccion and not municipios_restringidos:
        return queryset.none()

    filtros = Q()
    if orgs_sin_restriccion:
        filtros |= Q(hospital__organizacion_id__in=orgs_sin_restriccion)
        filtros |= Q(refugio__organizacion_id__in=orgs_sin_restriccion)
    if municipios_restringidos:
        filtros |= Q(
            hospital__organizacion_id__in=[
                m[0] for m in membresias if m[1] is not None
            ],
            hospital__municipio_id__in=municipios_restringidos,
        )
        filtros |= Q(
            refugio__organizacion_id__in=[
                m[0] for m in membresias if m[1] is not None
            ],
            refugio__municipio_id__in=municipios_restringidos,
        )

    return queryset.filter(filtros).distinct()
'''

if "def filtrar_episodios_por_ambito" not in text:
    svc_path.write_text(text.rstrip() + nuevo_bloque + "\n", encoding="utf-8")
    print("  OK: filtrar_episodios_por_ambito añadido")
else:
    print("  ya aplicado: filtro de ámbito")

# ══════════════════════════════════════════════════════════════════
# 3) App triaje
# ══════════════════════════════════════════════════════════════════
print("== 3/4 App triaje ==")
APP = BASE / "apps" / "triaje"
if APP.exists():
    print(f"  ya existe: {APP} (saltando)")
else:
    APP.mkdir(parents=True)
    (APP / "migrations").mkdir()
    (APP / "migrations" / "__init__.py").write_text("", encoding="utf-8")
    (APP / "__init__.py").write_text("", encoding="utf-8")

    w("apps/triaje/apps.py", '''from django.apps import AppConfig


class TriajeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.triaje"
    verbose_name = "Triaje"
''')

    w("apps/triaje/models.py", '''import uuid

from django.conf import settings
from django.db import models


class Triaje(models.Model):
    """
    Evaluación de triaje asociada a un Episodio.

    Sistema de clasificación: 3 niveles (ROJO/AMARILLO/VERDE) según práctica
    común en servicios de urgencia venezolanos y en el repositorio de origen
    `sistema-derivacion-hospitalaria`.

    Un episodio tiene MÚLTIPLES Triajes a lo largo del tiempo (inicial + 
    reevaluaciones). Solo uno tiene `vigente=True` en cada momento (garantizado
    por UniqueConstraint condicional).
    """

    class Clasificacion(models.TextChoices):
        ROJO = "ROJO", "Rojo — Emergencia vital, atención inmediata"
        AMARILLO = "AMARILLO", "Amarillo — Urgencia, atención prioritaria"
        VERDE = "VERDE", "Verde — No urgente, atención diferible"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episodio = models.ForeignKey(
        "pacientes.Episodio",
        on_delete=models.PROTECT,
        related_name="triajes",
    )
    clasificacion = models.CharField(
        max_length=10, choices=Clasificacion.choices, db_index=True
    )
    signos_vitales = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Claves esperadas: temperatura (C), frecuencia_cardiaca (lpm), "
            "frecuencia_respiratoria (rpm), presion_arterial_sistolica (mmHg), "
            "presion_arterial_diastolica (mmHg), saturacion_oxigeno (%), "
            "escala_glasgow (3-15), peso_kg, talla_cm."
        ),
    )
    observaciones = models.TextField(blank=True)
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="triajes_evaluados",
    )
    evaluado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    es_reevaluacion = models.BooleanField(default=False)
    motivo_reevaluacion = models.CharField(max_length=300, blank=True)
    vigente = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-evaluado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["episodio"],
                condition=models.Q(vigente=True),
                name="un_triaje_vigente_por_episodio",
            ),
        ]
        indexes = [
            models.Index(fields=["episodio", "-evaluado_en"]),
            models.Index(fields=["clasificacion", "-evaluado_en"]),
            models.Index(fields=["vigente", "-evaluado_en"]),
        ]
        verbose_name = "triaje"
        verbose_name_plural = "triajes"

    def __str__(self):
        return (
            f"{self.episodio_id} — {self.get_clasificacion_display()} "
            f"({'vigente' if self.vigente else 'histórico'})"
        )
''')

    w("apps/triaje/services.py", '''"""Servicios de triaje — creación transaccional y auditada."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.pacientes.models import Episodio
from apps.pacientes.services import filtrar_episodios_por_ambito
from apps.triaje.models import Triaje


@transaction.atomic
def registrar_triaje(
    *,
    episodio_id,
    clasificacion,
    signos_vitales=None,
    observaciones="",
    es_reevaluacion=False,
    motivo_reevaluacion="",
    usuario,
    request=None,
):
    """
    Registra un nuevo triaje para un episodio.

    - Bloquea el episodio con select_for_update (§10).
    - Verifica que el usuario tenga acceso al episodio (§8, §11).
    - Marca el triaje anterior vigente como histórico.
    - Crea el nuevo Triaje con vigente=True.
    - Audita la operación con hash encadenado.
    """
    clasificaciones_validas = {v for v, _ in Triaje.Clasificacion.choices}
    if clasificacion not in clasificaciones_validas:
        raise ValidationError(
            {"clasificacion": "La clasificación no es válida."}
        )

    if es_reevaluacion and not motivo_reevaluacion.strip():
        raise ValidationError(
            {"motivo_reevaluacion": "Debes justificar la reevaluación."}
        )

    try:
        episodio = (
            Episodio.objects
            .select_for_update()
            .select_related("paciente", "hospital", "refugio")
            .get(pk=episodio_id)
        )
    except Episodio.DoesNotExist:
        raise ValidationError({"episodio": "El episodio no existe."})

    # Verificación de ámbito (§8, §11): el usuario debe poder ver este episodio
    episodios_visibles = filtrar_episodios_por_ambito(
        Episodio.objects.filter(pk=episodio_id), usuario
    )
    if not episodios_visibles.exists():
        raise PermissionDenied(
            "No tienes acceso a este episodio (ámbito o organización)."
        )

    if episodio.estado in {Episodio.Estado.CERRADO, Episodio.Estado.FALLECIDO}:
        raise ValidationError(
            {"episodio": "No se puede triajar un episodio cerrado o fallecido."}
        )

    # Marca el anterior como histórico (respeta UniqueConstraint parcial)
    Triaje.objects.filter(episodio=episodio, vigente=True).update(vigente=False)

    triaje = Triaje.objects.create(
        episodio=episodio,
        clasificacion=clasificacion,
        signos_vitales=signos_vitales or {},
        observaciones=observaciones,
        evaluado_por=usuario,
        es_reevaluacion=es_reevaluacion,
        motivo_reevaluacion=motivo_reevaluacion,
        vigente=True,
    )

    ip = None
    user_agent = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    registrar_evento(
        actor=usuario,
        accion=(
            "triaje.reevaluacion_registrada"
            if es_reevaluacion
            else "triaje.registrado"
        ),
        tipo_objeto="Triaje",
        objeto_id=triaje.id,
        resultado=EventoAuditoria.Resultado.EXITOSO,
        justificacion=(
            f"Triaje {triaje.get_clasificacion_display()} "
            f"para episodio {episodio.pk}."
        ),
        direccion_ip=ip,
        agente_usuario=user_agent,
        metadatos={
            "episodio_id": str(episodio.pk),
            "clasificacion": clasificacion,
            "es_reevaluacion": es_reevaluacion,
            "tiene_signos_vitales": bool(triaje.signos_vitales),
        },
    )

    return triaje
''')

    w("apps/triaje/admin.py", '''from django.contrib import admin

from apps.triaje.models import Triaje


@admin.register(Triaje)
class TriajeAdmin(admin.ModelAdmin):
    list_display = (
        "episodio",
        "clasificacion",
        "vigente",
        "es_reevaluacion",
        "evaluado_por",
        "evaluado_en",
    )
    list_filter = ("clasificacion", "vigente", "es_reevaluacion")
    search_fields = (
        "episodio__paciente__apellidos",
        "episodio__paciente__nombres",
    )
    readonly_fields = (
        "id",
        "episodio",
        "clasificacion",
        "signos_vitales",
        "observaciones",
        "evaluado_por",
        "evaluado_en",
        "es_reevaluacion",
        "motivo_reevaluacion",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
''')

print("\n✅ Código escrito.")
