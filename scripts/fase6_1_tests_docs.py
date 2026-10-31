#!/usr/bin/env python3
"""Fase 6.1 — Tests y docs para hospitales."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3

# ══════════════════════════════════════════════════════════════════
# tests.py
# ══════════════════════════════════════════════════════════════════
tests_path = BASE / "apps" / "hospitales" / "tests.py"
tests_path.write_text('''from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import (
    Hospital,
    HospitalServicio,
    RecursoHospitalario,
    RegistroDisponibilidad,
    Servicio,
)
from apps.hospitales.services import registrar_disponibilidad
from apps.organizaciones.models import Organizacion

Usuario = get_user_model()


def _org(slug="h-org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.HOSPITAL,
        codigo=slug,
        estado=Organizacion.Estado.ACTIVA,
    )


def _hospital(org, slug="h-1"):
    return Hospital.objects.create(
        codigo=slug,
        nombre=f"Hospital {slug}",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="Calle x",
        estado_operativo=Hospital.EstadoOperativo.DISPONIBLE,
    )


class HospitalModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-m")

    def test_crear_hospital_valido(self):
        h = _hospital(self.org, "h-valid")
        self.assertEqual(h.tipo, Hospital.Tipo.HOSPITAL)
        self.assertEqual(h.nivel, Hospital.Nivel.NIVEL_III)
        self.assertEqual(h.estado_operativo, Hospital.EstadoOperativo.DISPONIBLE)

    def test_codigo_unico(self):
        _hospital(self.org, "h-dup")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _hospital(self.org, "h-dup")

    def test_servicios_m2m_through(self):
        h = _hospital(self.org, "h-svc")
        s = Servicio.objects.create(
            codigo="emergencia", nombre="Emergencia",
            tipo=Servicio.Tipo.SERVICIO,
        )
        HospitalServicio.objects.create(hospital=h, servicio=s, disponible=True)
        self.assertEqual(h.servicios.count(), 1)
        self.assertTrue(h.servicios_through.first().disponible)

    def test_unique_hospital_servicio(self):
        h = _hospital(self.org, "h-svc2")
        s = Servicio.objects.create(
            codigo="pediatria", nombre="Pediatría",
            tipo=Servicio.Tipo.ESPECIALIDAD,
        )
        HospitalServicio.objects.create(hospital=h, servicio=s)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HospitalServicio.objects.create(hospital=h, servicio=s)


class RecursoHospitalarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-r")
        cls.hospital = _hospital(cls.org, "h-rec")

    def test_unique_hospital_tipo(self):
        RecursoHospitalario.objects.create(
            hospital=self.hospital,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=5,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RecursoHospitalario.objects.create(
                    hospital=self.hospital,
                    tipo=RecursoHospitalario.Tipo.UCI,
                    capacidad_total=5,
                    disponible=2,
                )

    def test_check_disponible_le_capacidad_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RecursoHospitalario.objects.create(
                    hospital=self.hospital,
                    tipo=RecursoHospitalario.Tipo.URGENCIA,
                    capacidad_total=5,
                    disponible=10,
                )

    def test_ocupados_property(self):
        r = RecursoHospitalario.objects.create(
            hospital=self.hospital,
            tipo=RecursoHospitalario.Tipo.QUIROFANO,
            capacidad_total=4,
            disponible=1,
        )
        self.assertEqual(r.ocupados, 3)


class RegistrarDisponibilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-d")
        cls.usuario = Usuario.objects.create_user(username="h-u", password="x")
        cls.hospital = _hospital(cls.org, "h-disp")
        cls.recurso = RecursoHospitalario.objects.create(
            hospital=cls.hospital,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=3,
        )

    def test_actualiza_disponibilidad(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
        )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.disponible, 7)

    def test_crea_registro_historial(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
            notas="Ingreso de 4 pacientes",
        )
        self.assertEqual(RegistroDisponibilidad.objects.count(), 1)
        r = RegistroDisponibilidad.objects.first()
        self.assertEqual(r.cantidad_anterior, 3)
        self.assertEqual(r.cantidad_nueva, 7)
        self.assertEqual(r.diferencia, 4)

    def test_audita_cambio(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="hospital.disponibilidad_actualizada"
            ).count(),
            1,
        )

    def test_rechaza_exceso_capacidad(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id=self.recurso.id,
                cantidad_nueva=20,
                usuario=self.usuario,
            )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.disponible, 3)

    def test_rechaza_negativa(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id=self.recurso.id,
                cantidad_nueva=-1,
                usuario=self.usuario,
            )

    def test_idempotente_si_igual(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=3,
            usuario=self.usuario,
        )
        self.assertEqual(RegistroDisponibilidad.objects.count(), 0)

    def test_recurso_inexistente(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id="00000000-0000-0000-0000-000000000000",
                cantidad_nueva=1,
                usuario=self.usuario,
            )
''', encoding="utf-8")
print("  escrito: apps/hospitales/tests.py")

# ══════════════════════════════════════════════════════════════════
# data-dictionary.md — secciones 13-17
# ══════════════════════════════════════════════════════════════════
dd = BASE / "docs" / "data-dictionary.md"
text = dd.read_text(encoding="utf-8")

nuevas = f"""
## 13. `hospitales.Hospital`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(100) | Sí | **UNIQUE** | PUB | Sí |
| nombre | CharField(200) | Sí | — | PUB | Sí |
| tipo | CharField(20) | Sí | TextChoices | PUB | Sí |
| nivel | CharField(15) | Sí | TextChoices (Nivel I-IV) | PUB | Sí |
| organizacion | FK Organizacion | Sí | on_delete=PROTECT | OPE | Sí |
| responsable | FK Usuario | No | on_delete=PROTECT | OPE | Sí |
| ubicacion | PointField | No | SRID 4326 | PUB | Sí |
| direccion | CharField(300) | Sí | — | PUB | Sí |
| referencia_lugar | CharField(250) | No | — | PUB | Sí |
| municipio | FK Municipio | No | on_delete=PROTECT | PUB | Sí |
| parroquia | FK Parroquia | No | on_delete=PROTECT | PUB | Sí |
| telefono_publico | CharField(30) | No | — | PUB | Sí |
| correo_publico | EmailField | No | — | PUB | Sí |
| notas_internas | TextField | No | — | OPE | Sí |
| estado_operativo | CharField(20) | Sí | TextChoices, index | PUB | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

## 14. `hospitales.Servicio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | **UNIQUE** | PUB | — |
| nombre | CharField(150) | Sí | — | PUB | — |
| tipo | CharField(15) | Sí | SERVICIO/ESPECIALIDAD | PUB | — |
| activo | Boolean | Sí | default=True | PUB | — |

## 15. `hospitales.HospitalServicio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| hospital | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| servicio | FK Servicio | Sí | on_delete=PROTECT | OPE | Sí |
| disponible | Boolean | Sí | default=True | PUB | Sí |
| notas | TextField | No | — | OPE | Sí |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **UniqueConstraint(hospital, servicio).** Un hospital no puede declarar el
> mismo servicio dos veces.

## 16. `hospitales.RecursoHospitalario`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| hospital | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| tipo | CharField(20) | Sí | UCI/URGENCIA/QUIROFANO/HOSPITALIZACION | PUB | Sí |
| capacidad_total | PositiveInteger | Sí | default=0 | PUB | Sí |
| disponible | PositiveInteger | Sí | default=0, <= capacidad_total | PUB | Sí |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **CheckConstraint:** `disponible <= capacidad_total`.
> **UniqueConstraint(hospital, tipo).**

## 17. `hospitales.RegistroDisponibilidad`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| recurso | FK RecursoHospitalario | Sí | on_delete=PROTECT | OPE | Sí |
| cantidad_anterior | PositiveInteger | Sí | — | OPE | Sí |
| cantidad_nueva | PositiveInteger | Sí | — | OPE | Sí |
| diferencia | Integer | Sí | puede ser negativo | OPE | Sí |
| registrado_por | FK Usuario | No | on_delete=PROTECT | PER | Sí |
| notas | TextField | No | — | OPE | Sí |
| creado_en | DateTimeField | Sí | auto_now_add, index | OPE | — |

> **Historial inmutable.** Solo `registrar_disponibilidad()` crea registros.
> El admin no permite crear, modificar ni eliminar.
"""

if "## 13. `hospitales.Hospital`" not in text:
    dd.write_text(text.rstrip() + "\n" + nuevas, encoding="utf-8")
    print("  OK: data-dictionary.md ampliado (secciones 13-17)")
else:
    print("  ya aplicado: data-dictionary.md")

# ══════════════════════════════════════════════════════════════════
# entity-relationship.md — entidades + relaciones
# ══════════════════════════════════════════════════════════════════
er = BASE / "docs" / "entity-relationship.md"
text = er.read_text(encoding="utf-8")

# Insertar entidades antes de la primera relación
needle_entities = '\n\n    USUARIO ||--o{ MEMBRESIA : "tiene"\n'
nuevas_entidades = """
    HOSPITAL {
        uuid id PK
        string codigo UK
        string nombre
        string tipo
        string nivel
        uuid organizacion_id FK
        uuid responsable_id FK
        geometry ubicacion
        string direccion
        uuid municipio_id FK
        uuid parroquia_id FK
        string estado_operativo
        string telefono_publico
    }
    SERVICIO {
        uuid id PK
        string codigo UK
        string nombre
        string tipo
        boolean activo
    }
    HOSPITAL_SERVICIO {
        uuid id PK
        uuid hospital_id FK
        uuid servicio_id FK
        boolean disponible
    }
    RECURSO_HOSPITALARIO {
        uuid id PK
        uuid hospital_id FK
        string tipo
        int capacidad_total
        int disponible
    }
    REGISTRO_DISPONIBILIDAD {
        uuid id PK
        uuid recurso_id FK
        int cantidad_anterior
        int cantidad_nueva
        int diferencia
        uuid registrado_por_id FK
        datetime creado_en
    }
"""

if needle_entities in text and "    HOSPITAL {" not in text:
    text = text.replace(needle_entities, nuevas_entidades + needle_entities, 1)
    print("  OK: entidades de hospitales insertadas en ER")

# Insertar relaciones después de la última relación de refugios
needle_rel = '    USUARIO ||--o{ REGISTRO_OCUPACION : "registra"\n'
nuevas_relaciones = """    ORGANIZACION ||--o{ HOSPITAL : "administra"
    USUARIO ||--o{ HOSPITAL : "responsable"
    MUNICIPIO ||--o{ HOSPITAL : "ubica"
    PARROQUIA ||--o{ HOSPITAL : "ubica"
    HOSPITAL ||--o{ HOSPITAL_SERVICIO : "ofrece"
    SERVICIO ||--o{ HOSPITAL_SERVICIO : "en"
    HOSPITAL ||--o{ RECURSO_HOSPITALARIO : "tiene"
    RECURSO_HOSPITALARIO ||--o{ REGISTRO_DISPONIBILIDAD : "registra"
    USUARIO ||--o{ REGISTRO_DISPONIBILIDAD : "registra"
"""

if needle_rel in text and 'ORGANIZACION ||--o{ HOSPITAL : "administra"' not in text:
    text = text.replace(needle_rel, needle_rel + nuevas_relaciones, 1)
    print("  OK: relaciones de hospitales insertadas en ER")

# Actualizar tabla de pendientes
text = text.replace(
    "| `hospitales` | Fase 6 | organizaciones, territorio |",
    "| `hospitales` | **Fase 6.1 — implementado** | — |",
)

er.write_text(text, encoding="utf-8")
print("\n✅ Tests y docs escritos.")
