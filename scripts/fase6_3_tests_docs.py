#!/usr/bin/env python3
"""Fase 6.3 — tests + docs."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3

# ══════════════════════════════════════════════════════════════════
# Tests de ámbito (append a organizaciones/tests.py)
# ══════════════════════════════════════════════════════════════════
org_tests = BASE / "apps" / "organizaciones" / "tests.py"
if not org_tests.exists():
    org_tests.write_text("", encoding="utf-8")
existing = org_tests.read_text(encoding="utf-8")

nuevos_org = '''

# ══════════════════════════════════════════════════════════════════
# Ámbito territorial de Membresía (Fase 6.3)
# ══════════════════════════════════════════════════════════════════

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.organizaciones.models import Membresia, Organizacion
from apps.territorio.models import EntidadFederal, Municipio

Usuario = get_user_model()


class AmbitoMembresiaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(
            nombre="Org Ámbito",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="org-ambito",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.entidad = EntidadFederal.objects.create(
            nombre="Distrito Capital",
            codigo="DC",
            tipo=EntidadFederal.Tipo.ESTADO,
        )
        cls.municipio_a = Municipio.objects.create(
            entidad_federal=cls.entidad,
            nombre="Libertador",
            codigo="DC-LIB",
        )
        cls.municipio_b = Municipio.objects.create(
            entidad_federal=cls.entidad,
            nombre="Chacao",
            codigo="DC-CHA",
        )
        cls.usuario_sin = Usuario.objects.create_user(
            username="sin-ambito", password="x"
        )
        cls.usuario_con = Usuario.objects.create_user(
            username="con-ambito", password="x"
        )

    def test_membresia_sin_ambito_default_null(self):
        m = Membresia.objects.create(
            usuario=self.usuario_sin,
            organizacion=self.org,
            rol=Membresia.Rol.SANITARIO,
            estado=Membresia.Estado.ACTIVA,
        )
        self.assertIsNone(m.ambito_municipio)

    def test_membresia_con_ambito(self):
        m = Membresia.objects.create(
            usuario=self.usuario_con,
            organizacion=self.org,
            rol=Membresia.Rol.SANITARIO,
            estado=Membresia.Estado.ACTIVA,
            ambito_municipio=self.municipio_a,
        )
        self.assertEqual(m.ambito_municipio, self.municipio_a)
'''

if "class AmbitoMembresiaTests" not in existing:
    org_tests.write_text(existing + nuevos_org, encoding="utf-8")
    print("  OK: organizaciones/tests.py +2 tests")
else:
    print("  ya aplicado: organizaciones/tests.py")

# ══════════════════════════════════════════════════════════════════
# Tests de filtro de episodios (append a pacientes/tests.py)
# ══════════════════════════════════════════════════════════════════
pac_tests = BASE / "apps" / "pacientes" / "tests.py"
existing = pac_tests.read_text(encoding="utf-8")

nuevos_pac = '''

# ══════════════════════════════════════════════════════════════════
# Filtro de ámbito para Episodios (Fase 6.3)
# ══════════════════════════════════════════════════════════════════

from apps.organizaciones.models import Membresia
from apps.territorio.models import EntidadFederal, Municipio as Mun


class FiltradoEpisodiosPorAmbitoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_operador = Usuario.objects.create_user(
            username="amb-op", password="x"
        )
        cls.usuario_sin = Usuario.objects.create_user(
            username="amb-sin", password="x"
        )
        cls.superuser = Usuario.objects.create_user(
            username="amb-super", password="x", is_superuser=True
        )
        cls.org = Organizacion.objects.create(
            nombre="Org Episodios",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="org-ep",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.entidad = EntidadFederal.objects.create(
            nombre="Zulia", codigo="ZUL", tipo=EntidadFederal.Tipo.ESTADO,
        )
        cls.municipio_a = Mun.objects.create(
            entidad_federal=cls.entidad, nombre="Maracaibo", codigo="ZUL-MAR",
        )
        cls.municipio_b = Mun.objects.create(
            entidad_federal=cls.entidad, nombre="Cabimas", codigo="ZUL-CAB",
        )
        cls.hospital_a = Hospital.objects.create(
            codigo="h-amb-a",
            nombre="Hospital A",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III,
            organizacion=cls.org,
            direccion="x",
            municipio=cls.municipio_a,
        )
        cls.hospital_b = Hospital.objects.create(
            codigo="h-amb-b",
            nombre="Hospital B",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III,
            organizacion=cls.org,
            direccion="y",
            municipio=cls.municipio_b,
        )
        cls.paciente = crear_paciente(
            nombres="Filtrado", apellidos="Test",
            usuario=cls.usuario_operador,
        )
        cls.ep_a = Episodio.objects.create(
            paciente=cls.paciente,
            hospital=cls.hospital_a,
            motivo_consulta="x",
            registrado_por=cls.usuario_operador,
        )
        cls.ep_b = Episodio.objects.create(
            paciente=cls.paciente,
            hospital=cls.hospital_b,
            motivo_consulta="y",
            registrado_por=cls.usuario_operador,
        )

    def test_sin_membresia_no_ve_nada(self):
        from apps.pacientes.services import filtrar_episodios_por_ambito
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.usuario_sin
        )
        self.assertEqual(qs.count(), 0)

    def test_sin_ambito_ve_todo_lo_de_su_org(self):
        Membresia.objects.create(
            usuario=self.usuario_operador,
            organizacion=self.org,
            rol=Membresia.Rol.SANITARIO,
            estado=Membresia.Estado.ACTIVA,
        )
        from apps.pacientes.services import filtrar_episodios_por_ambito
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.usuario_operador
        )
        self.assertEqual(qs.count(), 2)

    def test_con_ambito_ve_solo_su_municipio(self):
        Membresia.objects.create(
            usuario=self.usuario_operador,
            organizacion=self.org,
            rol=Membresia.Rol.SANITARIO,
            estado=Membresia.Estado.ACTIVA,
            ambito_municipio=self.municipio_a,
        )
        from apps.pacientes.services import filtrar_episodios_por_ambito
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.usuario_operador
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), self.ep_a)

    def test_superuser_ve_todo(self):
        from apps.pacientes.services import filtrar_episodios_por_ambito
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.superuser
        )
        self.assertEqual(qs.count(), 2)
'''

if "class FiltradoEpisodiosPorAmbitoTests" not in existing:
    pac_tests.write_text(existing + nuevos_pac, encoding="utf-8")
    print("  OK: pacientes/tests.py +4 tests")
else:
    print("  ya aplicado: pacientes/tests.py")

# ══════════════════════════════════════════════════════════════════
# tests.py de triaje
# ══════════════════════════════════════════════════════════════════
triaje_tests = BASE / "apps" / "triaje" / "tests.py"
triaje_tests.write_text('''from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Membresia, Organizacion
from apps.pacientes.models import Episodio
from apps.pacientes.services import crear_paciente
from apps.triaje.models import Triaje
from apps.triaje.services import registrar_triaje

Usuario = get_user_model()


def _setup_basico():
    org = Organizacion.objects.create(
        nombre="Org Triaje",
        tipo=Organizacion.Tipo.HOSPITAL,
        codigo="org-triage",
        estado=Organizacion.Estado.ACTIVA,
    )
    hospital = Hospital.objects.create(
        codigo="h-triage",
        nombre="Hospital Triage",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="x",
    )
    usuario = Usuario.objects.create_user(username="triage-u", password="x")
    Membresia.objects.create(
        usuario=usuario,
        organizacion=org,
        rol=Membresia.Rol.SANITARIO,
        estado=Membresia.Estado.ACTIVA,
    )
    paciente = crear_paciente(
        nombres="Triaje", apellidos="Test", usuario=usuario,
    )
    episodio = Episodio.objects.create(
        paciente=paciente,
        hospital=hospital,
        motivo_consulta="Dolor abdominal",
        registrado_por=usuario,
    )
    return org, hospital, usuario, paciente, episodio


class RegistrarTriajeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.hospital, cls.usuario, cls.paciente, cls.episodio = _setup_basico()

    def test_triaje_inicial(self):
        t = registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.AMARILLO,
            signos_vitales={"temperatura": 38.5, "frecuencia_cardiaca": 95},
            usuario=self.usuario,
        )
        self.assertTrue(t.vigente)
        self.assertFalse(t.es_reevaluacion)
        self.assertEqual(t.clasificacion, Triaje.Clasificacion.AMARILLO)

    def test_reevaluacion_marca_anterior_historico(self):
        t1 = registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.AMARILLO,
            usuario=self.usuario,
        )
        t2 = registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.ROJO,
            es_reevaluacion=True,
            motivo_reevaluacion="Empeoramiento",
            usuario=self.usuario,
        )
        t1.refresh_from_db()
        self.assertFalse(t1.vigente)
        self.assertTrue(t2.vigente)
        self.assertEqual(
            Triaje.objects.filter(episodio=self.episodio, vigente=True).count(), 1
        )

    def test_reevaluacion_sin_motivo_falla(self):
        with self.assertRaises(ValidationError):
            registrar_triaje(
                episodio_id=self.episodio.pk,
                clasificacion=Triaje.Clasificacion.VERDE,
                es_reevaluacion=True,
                motivo_reevaluacion="",
                usuario=self.usuario,
            )

    def test_clasificacion_invalida_falla(self):
        with self.assertRaises(ValidationError):
            registrar_triaje(
                episodio_id=self.episodio.pk,
                clasificacion="INVENTADO",
                usuario=self.usuario,
            )

    def test_sin_acceso_falla(self):
        usuario_ajeno = Usuario.objects.create_user(
            username="triage-ajeno", password="x"
        )
        with self.assertRaises(PermissionDenied):
            registrar_triaje(
                episodio_id=self.episodio.pk,
                clasificacion=Triaje.Clasificacion.VERDE,
                usuario=usuario_ajeno,
            )

    def test_episodio_inexistente_falla(self):
        with self.assertRaises(ValidationError):
            registrar_triaje(
                episodio_id="00000000-0000-0000-0000-000000000000",
                clasificacion=Triaje.Clasificacion.VERDE,
                usuario=self.usuario,
            )

    def test_audita_triaje(self):
        registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.VERDE,
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(accion="triaje.registrado").count(),
            1,
        )

    def test_audita_reevaluacion(self):
        registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.VERDE,
            usuario=self.usuario,
        )
        registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.AMARILLO,
            es_reevaluacion=True,
            motivo_reevaluacion="Cambio",
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="triaje.reevaluacion_registrada"
            ).count(),
            1,
        )


class UnicidadVigenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.hospital, cls.usuario, cls.paciente, cls.episodio = _setup_basico()

    def test_dos_vigentes_falla_db(self):
        Triaje.objects.create(
            episodio=self.episodio,
            clasificacion=Triaje.Clasificacion.VERDE,
            evaluado_por=self.usuario,
            vigente=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Triaje.objects.create(
                    episodio=self.episodio,
                    clasificacion=Triaje.Clasificacion.ROJO,
                    evaluado_por=self.usuario,
                    vigente=True,
                )
''', encoding="utf-8")
print("  escrito: apps/triaje/tests.py (9 tests)")

# ══════════════════════════════════════════════════════════════════
# data-dictionary.md
# ══════════════════════════════════════════════════════════════════
dd = BASE / "docs" / "data-dictionary.md"
text = dd.read_text(encoding="utf-8")

nuevas = f"""
## 21. `triaje.Triaje`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | CLI | — |
| episodio | FK Episodio | Sí | on_delete=PROTECT | CLI | Sí |
| clasificacion | CharField(10) | Sí | ROJO/AAMARILLO/VERDE, index | CLI | Sí |
| signos_vitales | JSONField | No | default=dict | CLI | Sí |
| observaciones | TextField | No | — | CLI | Sí |
| evaluado_por | FK Usuario | Sí | on_delete=PROTECT | PER | Sí |
| evaluado_en | DateTimeField | Sí | auto_now_add, index | CLI | — |
| es_reevaluacion | Boolean | Sí | default=False | CLI | Sí |
| motivo_reevaluacion | CharField(300) | No | obligatorio si es_reevaluacion | CLI | Sí |
| vigente | Boolean | Sí | default=True, index | CLI | Sí |

> **`UniqueConstraint` parcial** (`un_triaje_vigente_por_episodio`):
> solo un triaje vigente por episodio. Los anteriores quedan como
> históricos (`vigente=False`) pero nunca se borran.
>
> **Sistema de clasificación:** 3 niveles (ROJO/AAMARILLO/VERDE), basado
> en la práctica común de servicios de urgencia venezolanos y en el repo
> de origen `sistema-derivacion-hospitalaria`. Un proveedor puede adoptar
> 4-5 niveles si su protocolo clínico lo exige; se actualiza el `TextChoices`.
>
> **Claves esperadas en `signos_vitales`:** `temperatura` (°C),
> `frecuencia_cardiaca` (lpm), `frecuencia_respiratoria` (rpm),
> `presion_arterial_sistolica` (mmHg), `presion_arterial_diastolica` (mmHg),
> `saturacion_oxigeno` (%), `escala_glasgow` (3-15), `peso_kg`, `talla_cm`.
> No hay validación estricta de claves en Fase 6.3 (JSONB flexible).
>
> **`Membresia.ambito_municipio`** (Fase 6.3): nueva FK nullable. Si
> definida, restringe el acceso del usuario a episodios del municipio.
> Afecta a `filtrar_episodios_por_ambito()` en
> `apps/pacientes/services.py`.
"""

if "## 21. `triaje.Triaje`" not in text:
    dd.write_text(text.rstrip() + "\n" + nuevas, encoding="utf-8")
    print("  OK: data-dictionary.md ampliado (sección 21)")

# ══════════════════════════════════════════════════════════════════
# entity-relationship.md
# ══════════════════════════════════════════════════════════════════
er = BASE / "docs" / "entity-relationship.md"
text = er.read_text(encoding="utf-8")

needle_entities = '\n\n    USUARIO ||--o{ MEMBRESIA : "tiene"\n'
nuevas_entidades = """
    TRIAJE {
        uuid id PK
        uuid episodio_id FK
        string clasificacion
        jsonb signos_vitales
        text observaciones
        uuid evaluado_por_id FK
        datetime evaluado_en
        boolean es_reevaluacion
        boolean vigente
    }
"""

if "    TRIAJE {" not in text:
    text = text.replace(needle_entities, nuevas_entidades + needle_entities, 1)
    print("  OK: entidad Triaje insertada en ER")

needle_rel = '    PACIENTE ||--o{ CONTACTO_EMERGENCIA : "tiene"\n'
nuevas_relaciones = """    EPISODIO ||--o{ TRIAJE : "tiene"
    USUARIO ||--o{ TRIAJE : "evalua"
"""

if 'EPISODIO ||--o{ TRIAJE' not in text:
    text = text.replace(needle_rel, needle_rel + nuevas_relaciones, 1)
    print("  OK: relaciones de Triaje insertadas en ER")

text = text.replace(
    "| `triaje` | Fase 6 | pacientes |",
    "| `triaje` | **Fase 6.3 — implementado** | — |",
)

er.write_text(text, encoding="utf-8")

# ══════════════════════════════════════════════════════════════════
# permissions.md — cerrar decisión de ámbito
# ══════════════════════════════════════════════════════════════════
perm = BASE / "docs" / "permissions.md"
text = perm.read_text(encoding="utf-8")

needle = "- **Fase 6 (pacientes):** implementación obligatoria. El riesgo de\n      filtración clínica excede el costo de complejidad."
nuevo = (
    "- **Fase 6 (pacientes):** **IMPLEMENTADO en Fase 6.3** — se añadió\n"
    "      `Membresia.ambito_municipio` como FK nullable (PROTECT).\n"
    "      - Si `NULL`: sin restricción geográfica dentro de la organización.\n"
    "      - Si definido: solo accede a episodios cuyo hospital/refugio esté\n"
    "        en ese municipio.\n"
    "      - Ver `apps/pacientes/services.filtrar_episodios_por_ambito()`.\n"
    "      - Decisión híbrida B+C: no rompe membresías existentes, pero\n"
    "        permite granularidad cuando se necesite. Se reevalúa en Fase 7\n"
    "        si aparece necesidad de múltiples municipios por usuario\n"
    "        (requeriría M2M, no añadir campo)."
)

if needle in text:
    perm.write_text(text.replace(needle, nuevo, 1), encoding="utf-8")
    print("  OK: permissions.md §7 actualizado (ámbito implementado)")
else:
    print("  nota: permissions.md sin cambio (patrón no encontrado)")

print("\n✅ Tests y docs escritos.")
