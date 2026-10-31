from datetime import date, timedelta

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


# ══════════════════════════════════════════════════════════════════
# Filtro de ámbito para Episodios (Fase 6.3)
# ══════════════════════════════════════════════════════════════════

from apps.organizaciones.models import Membresia
from apps.territorio.models import EntidadFederal, Municipio as Mun


class FiltradoEpisodiosPorAmbitoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_operador = Usuario.objects.create_user(
            username="amb-op", email="amb-op@test.local", password="x"
        )
        cls.usuario_sin = Usuario.objects.create_user(
            username="amb-sin", email="amb-sin@test.local", password="x"
        )
        cls.superuser = Usuario.objects.create_user(
            username="amb-super", email="amb-super@test.local",
            password="x", is_superuser=True
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
