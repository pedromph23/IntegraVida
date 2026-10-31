from django.contrib.auth import get_user_model
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
