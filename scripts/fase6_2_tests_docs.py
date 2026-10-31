#!/usr/bin/env python3
"""Fase 6.2 — tests + docs para pacientes."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3

# ══════════════════════════════════════════════════════════════════
# tests.py
# ══════════════════════════════════════════════════════════════════
tests_path = BASE / "apps" / "pacientes" / "tests.py"
tests_path.write_text('''from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Organizacion
from apps.pacientes.models import ContactoEmergencia, Episodio, Paciente
from apps.pacientes.services import (
    buscar_paciente_por_cedula,
    calcular_cedula_hash,
    crear_paciente,
    normalizar_cedula,
)
from apps.refugios.models import Refugio

Usuario = get_user_model()


def _org(slug="p-org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.HOSPITAL,
        codigo=slug,
        estado=Organizacion.Estado.ACTIVA,
    )


def _hospital(org, slug="h-p"):
    return Hospital.objects.create(
        codigo=slug,
        nombre=f"Hospital {slug}",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="x",
    )


def _refugio(org, slug="r-p"):
    return Refugio.objects.create(
        codigo=slug,
        nombre=f"Refugio {slug}",
        organizacion=org,
        direccion="x",
        capacidad_total=10,
    )


class NormalizacionCedulaTests(TestCase):
    def test_normalizacion_simple(self):
        self.assertEqual(normalizar_cedula("V-12345678"), "V12345678")
        self.assertEqual(normalizar_cedula("v 12.345.678"), "V12345678")
        self.assertEqual(normalizar_cedula("12345678"), "12345678")
        self.assertEqual(normalizar_cedula(""), "")

    def test_hash_deterministico(self):
        h1 = calcular_cedula_hash("V-12345678")
        h2 = calcular_cedula_hash("v12345678")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hash_vacio_si_cedula_vacia(self):
        self.assertIsNone(calcular_cedula_hash(""))
        self.assertIsNone(calcular_cedula_hash(None))

    def test_hash_diferente_para_cedulas_diferentes(self):
        self.assertNotEqual(
            calcular_cedula_hash("V-11111111"),
            calcular_cedula_hash("V-22222222"),
        )


class CrearPacienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(username="p-u", password="x")

    def test_crear_paciente_con_cedula(self):
        p = crear_paciente(
            cedula="V-12345678",
            nombres="Ana",
            apellidos="Pérez",
            usuario=self.usuario,
        )
        self.assertIsNotNone(p.cedula_hash)
        self.assertEqual(len(p.cedula_hash), 64)
        self.assertEqual(p.nombres, "Ana")

    def test_crear_paciente_sin_cedula(self):
        p = crear_paciente(
            nombres="Sin",
            apellidos="Cédula",
            usuario=self.usuario,
        )
        self.assertIsNone(p.cedula_hash)
        self.assertEqual(p.cedula, "")

    def test_cedula_duplicada_falla(self):
        crear_paciente(
            cedula="V-99999999",
            nombres="Primero",
            apellidos="P",
            usuario=self.usuario,
        )
        with self.assertRaises(ValidationError):
            crear_paciente(
                cedula="v99999999",
                nombres="Segundo",
                apellidos="Q",
                usuario=self.usuario,
            )

    def test_sin_nombres_falla(self):
        with self.assertRaises(ValidationError):
            crear_paciente(
                cedula="V-1",
                nombres="",
                apellidos="P",
                usuario=self.usuario,
            )

    def test_audita_creacion(self):
        crear_paciente(
            cedula="V-55555555",
            nombres="Audit",
            apellidos="Test",
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(accion="paciente.creado").count(),
            1,
        )

    def test_dos_pacientes_sin_cedula_conviven(self):
        crear_paciente(
            nombres="Uno", apellidos="Sin", usuario=self.usuario,
        )
        crear_paciente(
            nombres="Dos", apellidos="Sin", usuario=self.usuario,
        )
        self.assertEqual(Paciente.objects.filter(cedula_hash__isnull=True).count(), 2)

    def test_buscar_por_cedula(self):
        p = crear_paciente(
            cedula="V-77777777",
            nombres="Buscar",
            apellidos="Test",
            usuario=self.usuario,
        )
        encontrado = buscar_paciente_por_cedula("v-77777777")
        self.assertEqual(encontrado, p)
        self.assertIsNone(buscar_paciente_por_cedula("V-00000000"))
        self.assertIsNone(buscar_paciente_por_cedula(""))


class EdadPropertyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(username="p-edad", password="x")

    def test_edad_calculada(self):
        hace_30 = date.today() - timedelta(days=365 * 30)
        p = crear_paciente(
            nombres="Edad",
            apellidos="Test",
            fecha_nacimiento=hace_30,
            usuario=self.usuario,
        )
        self.assertIn(p.edad, [29, 30])

    def test_edad_none_sin_fecha(self):
        p = crear_paciente(
            nombres="Sin",
            apellidos="Fecha",
            usuario=self.usuario,
        )
        self.assertIsNone(p.edad)


class ContactoEmergenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(username="p-cto", password="x")
        cls.paciente = crear_paciente(
            nombres="Contacto",
            apellidos="Test",
            usuario=cls.usuario,
        )

    def test_crear_contacto(self):
        c = ContactoEmergencia.objects.create(
            paciente=self.paciente,
            nombre="María",
            parentesco=ContactoEmergencia.Parentesco.MADRE,
            telefono="0414-0000000",
            es_principal=True,
        )
        self.assertEqual(self.paciente.contactos.count(), 1)
        self.assertTrue(c.es_principal)

    def test_solo_un_contacto_principal(self):
        ContactoEmergencia.objects.create(
            paciente=self.paciente,
            nombre="Uno",
            parentesco=ContactoEmergencia.Parentesco.PADRE,
            telefono="111",
            es_principal=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContactoEmergencia.objects.create(
                    paciente=self.paciente,
                    nombre="Dos",
                    parentesco=ContactoEmergencia.Parentesco.MADRE,
                    telefono="222",
                    es_principal=True,
                )

    def test_multiples_no_principales_permitidos(self):
        ContactoEmergencia.objects.create(
            paciente=self.paciente,
            nombre="Uno",
            parentesco=ContactoEmergencia.Parentesco.PADRE,
            telefono="111",
            es_principal=False,
        )
        ContactoEmergencia.objects.create(
            paciente=self.paciente,
            nombre="Dos",
            parentesco=ContactoEmergencia.Parentesco.MADRE,
            telefono="222",
            es_principal=False,
        )
        self.assertEqual(self.paciente.contactos.count(), 2)


class EpisodioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(username="p-ep", password="x")
        cls.org = _org("p-ep-org")
        cls.hospital = _hospital(cls.org, "h-ep")
        cls.refugio = _refugio(cls.org, "r-ep")
        cls.paciente = crear_paciente(
            nombres="Episodio",
            apellidos="Test",
            usuario=cls.usuario,
        )

    def test_episodio_en_hospital(self):
        ep = Episodio.objects.create(
            paciente=self.paciente,
            hospital=self.hospital,
            motivo_consulta="Dolor torácico",
            registrado_por=self.usuario,
        )
        self.assertIsNotNone(ep.hospital)
        self.assertIsNone(ep.refugio)

    def test_episodio_en_refugio(self):
        ep = Episodio.objects.create(
            paciente=self.paciente,
            refugio=self.refugio,
            motivo_consulta="Evaluación general",
            registrado_por=self.usuario,
        )
        self.assertIsNotNone(ep.refugio)
        self.assertIsNone(ep.hospital)

    def test_episodio_con_ambos_falla(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Episodio.objects.create(
                    paciente=self.paciente,
                    hospital=self.hospital,
                    refugio=self.refugio,
                    motivo_consulta="Inválido",
                    registrado_por=self.usuario,
                )

    def test_episodio_sin_centro_falla(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Episodio.objects.create(
                    paciente=self.paciente,
                    motivo_consulta="Sin centro",
                    registrado_por=self.usuario,
                )

    def test_fecha_egreso_anterior_falla(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Episodio.objects.create(
                    paciente=self.paciente,
                    hospital=self.hospital,
                    motivo_consulta="x",
                    fecha_ingreso=timezone.now(),
                    fecha_egreso=timezone.now() - timedelta(days=1),
                    registrado_por=self.usuario,
                )

    def test_fecha_egreso_posterior_ok(self):
        ep = Episodio.objects.create(
            paciente=self.paciente,
            hospital=self.hospital,
            motivo_consulta="x",
            fecha_ingreso=timezone.now() - timedelta(hours=2),
            fecha_egreso=timezone.now(),
            registrado_por=self.usuario,
        )
        self.assertIsNotNone(ep.fecha_egreso)

    def test_estado_default_abierto(self):
        ep = Episodio.objects.create(
            paciente=self.paciente,
            hospital=self.hospital,
            motivo_consulta="x",
            registrado_por=self.usuario,
        )
        self.assertEqual(ep.estado, Episodio.Estado.ABIERTO)
''', encoding="utf-8")
print("  escrito: apps/pacientes/tests.py (16 tests)")

# ══════════════════════════════════════════════════════════════════
# data-dictionary.md — secciones 18, 19, 20
# ══════════════════════════════════════════════════════════════════
dd = BASE / "docs" / "data-dictionary.md"
text = dd.read_text(encoding="utf-8")

nuevas = f"""
## 18. `pacientes.Paciente`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | PER | — |
| cedula | CharField(20) | No | blank, plaintext | **PER** | Sí |
| cedula_hash | CharField(64) | No | **UNIQUE**, index, nullable | **PER** (seudonimizado) | — |
| nombres | CharField(200) | Sí | — | **PER** | Sí |
| apellidos | CharField(200) | Sí | — | **PER** | Sí |
| fecha_nacimiento | DateField | No | — | **PER** | Sí |
| sexo_biologico | CharField(1) | Sí | F/M/I/N | **PER** | Sí |
| telefono | CharField(30) | No | — | **PER** | Sí |
| email | EmailField | No | — | **PER** | Sí |
| cuenta_vinculada | FK Usuario | No | on_delete=SET_NULL | **PER** | Sí |
| notas_internas | TextField | No | — | **CLI** | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **`cedula_hash`**: HMAC-SHA256 de la cédula normalizada (mayúsculas
> alfanuméricas). Permite detectar duplicados y buscar por cédula sin
> almacenar la cédula en claro indexada.
>
> **Cifrado diferido (decisión Fase 6.2):** los campos `PER` se almacenan
> en plaintext en Fase 6.2, protegidos por LUKS en producción (Fase 11)
> y HTTPS en tránsito. En Fase 11 se migran a cifrado a nivel de campo
> (AES) sin cambiar el schema relacional. **Decisión documentada en
> `docs/privacy-and-retention.md` §5.**
>
> **`__str__`**: `apellidos, nombres`. No incluye cédula (evita exposición
> en logs de Django).

## 19. `pacientes.ContactoEmergencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | PER | — |
| paciente | FK Paciente | Sí | on_delete=PROTECT | PER | Sí |
| nombre | CharField(200) | Sí | — | **PER** | Sí |
| parentesco | CharField(20) | Sí | TextChoices | PER | Sí |
| telefono | CharField(30) | Sí | — | **PER** | Sí |
| es_principal | Boolean | Sí | default=False | PER | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |

> **UniqueConstraint** parcial: un solo `es_principal=True` por paciente
> (`condition=Q(es_principal=True)`). Múltiples contactos secundarios OK.

## 20. `pacientes.Episodio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | CLI | — |
| paciente | FK Paciente | Sí | on_delete=PROTECT | CLI | Sí |
| hospital | FK Hospital | No* | on_delete=PROTECT | OPE | Sí |
| refugio | FK Refugio | No* | on_delete=PROTECT | OPE | Sí |
| motivo_consulta | TextField | Sí | — | **CLI** | Sí |
| estado | CharField(15) | Sí | TextChoices, index | CLI | Sí |
| fecha_ingreso | DateTimeField | Sí | default=now | CLI | Sí |
| fecha_egreso | DateTimeField | No | — | CLI | Sí |
| registrado_por | FK Usuario | Sí | on_delete=PROTECT | PER | Sí |
| notas_internas | TextField | No | — | **CLI** | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **`CheckConstraint` XOR (`episodio_uno_y_solo_un_centro`):**
> exactamente uno de `hospital_id` o `refugio_id` debe estar presente.
> Un episodio ambulatorio puro no está permitido en esta fase — requiere
> al menos un centro (hospital o refugio).
>
> **`CheckConstraint` (`episodio_egreso_posterior_a_ingreso`):**
> `fecha_egreso IS NULL OR fecha_egreso >= fecha_ingreso`.
>
> **Estados:** ABIERTO, EN_ATENCION, DERIVADO, CERRADO, FALLECIDO, ABANDONO.
"""

if "## 18. `pacientes.Paciente`" not in text:
    dd.write_text(text.rstrip() + "\n" + nuevas, encoding="utf-8")
    print("  OK: data-dictionary.md ampliado (secciones 18-20)")
else:
    print("  ya aplicado: data-dictionary.md")

# ══════════════════════════════════════════════════════════════════
# entity-relationship.md
# ══════════════════════════════════════════════════════════════════
er = BASE / "docs" / "entity-relationship.md"
text = er.read_text(encoding="utf-8")

needle_entities = '\n\n    USUARIO ||--o{ MEMBRESIA : "tiene"\n'
nuevas_entidades = """
    PACIENTE {
        uuid id PK
        string cedula
        string cedula_hash UK
        string nombres
        string apellidos
        date fecha_nacimiento
        string sexo_biologico
        string telefono
        uuid cuenta_vinculada_id FK
    }
    CONTACTO_EMERGENCIA {
        uuid id PK
        uuid paciente_id FK
        string nombre
        string parentesco
        string telefono
        boolean es_principal
    }
    EPISODIO {
        uuid id PK
        uuid paciente_id FK
        uuid hospital_id FK
        uuid refugio_id FK
        text motivo_consulta
        string estado
        datetime fecha_ingreso
        datetime fecha_egreso
        uuid registrado_por_id FK
    }
"""

if needle_entities in text and "    PACIENTE {" not in text:
    text = text.replace(needle_entities, nuevas_entidades + needle_entities, 1)
    print("  OK: entidades de pacientes insertadas en ER")

needle_rel = '    USUARIO ||--o{ REGISTRO_DISPONIBILIDAD : "registra"\n'
nuevas_relaciones = """    PACIENTE ||--o{ CONTACTO_EMERGENCIA : "tiene"
    PACIENTE ||--o{ EPISODIO : "tiene"
    HOSPITAL ||--o{ EPISODIO : "atiende"
    REFUGIO ||--o{ EPISODIO : "aloja"
    USUARIO ||--o{ EPISODIO : "registra"
    USUARIO ||--o| PACIENTE : "vinculado"
"""

if needle_rel in text and 'PACIENTE ||--o{ CONTACTO_EMERGENCIA' not in text:
    text = text.replace(needle_rel, needle_rel + nuevas_relaciones, 1)
    print("  OK: relaciones de pacientes insertadas en ER")

text = text.replace(
    "| `pacientes` | Fase 6 | requiere `docs/privacy-and-retention.md` antes |",
    "| `pacientes` | **Fase 6.2 — implementado** | — |",
)

er.write_text(text, encoding="utf-8")

# ══════════════════════════════════════════════════════════════════
# privacy-and-retention.md — cerrar pendiente de cifrado
# ══════════════════════════════════════════════════════════════════
pr = BASE / "docs" / "privacy-and-retention.md"
text = pr.read_text(encoding="utf-8")

old_pendiente = "- [ ] Definir si se aplica cifrado a nivel de campo para datos `CLI`\n      (decisión bloqueante para Fase 6)."
new_pendiente = (
    "- [x] ~~Definir si se aplica cifrado a nivel de campo para datos `CLI`~~\n"
    "      **DECIDIDO en Fase 6.2:** cifrado diferido a Fase 11. Los campos\n"
    "      `PER`/`CLI` se almacenan plaintext en Fase 6.2, protegidos por LUKS\n"
    "      (producción) y HTTPS. `cedula_hash` (HMAC-SHA256) permite detección\n"
    "      de duplicados y búsqueda sin plaintext indexado. Migración a AES\n"
    "      en Fase 11 **sin schema change** (solo data migration)."
)

if old_pendiente in text:
    text = text.replace(old_pendiente, new_pendiente, 1)
    pr.write_text(text, encoding="utf-8")
    print("  OK: privacy-and-retention.md actualizado (cifrado decidido)")
else:
    print("  nota: privacy-and-retention.md sin cambio (patrón no encontrado)")

print("\n✅ Tests y docs escritos.")
