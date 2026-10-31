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


# ══════════════════════════════════════════════════════════════════
# Cifrado de campos clínicos (Fase 11.1)
# ══════════════════════════════════════════════════════════════════

from django.db import connection


class CifradoCamposPacienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="cif-u", email="cif-u@test.local", password="x",
        )

    def test_roundtrip_cifrado(self):
        p = crear_paciente(
            cedula="V-12345678",
            nombres="Ana María",
            apellidos="Pérez González",
            telefono="0414-1234567",
            email="ana@test.local",
            notas_internas="Paciente con alergia a penicilina",
            usuario=self.usuario,
        )
        p_fresco = Paciente.objects.get(pk=p.pk)
        self.assertEqual(p_fresco.cedula, "V-12345678")
        self.assertEqual(p_fresco.nombres, "Ana María")
        self.assertEqual(p_fresco.apellidos, "Pérez González")
        self.assertEqual(p_fresco.telefono, "0414-1234567")
        self.assertEqual(p_fresco.email, "ana@test.local")
        self.assertEqual(
            p_fresco.notas_internas,
            "Paciente con alergia a penicilina",
        )

    def test_datos_cifrados_en_bd(self):
        p = crear_paciente(
            cedula="V-87654321",
            nombres="Carlos",
            apellidos="Rodríguez",
            usuario=self.usuario,
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT cedula, nombres, apellidos "
                "FROM pacientes_paciente WHERE id = %s",
                [str(p.pk)],
            )
            row = cur.fetchone()

        cedula_raw, nombres_raw, apellidos_raw = row

        # Los valores crudos en la BD NO deben ser el plaintext
        self.assertNotEqual(cedula_raw, "V-87654321")
        self.assertNotEqual(nombres_raw, "Carlos")
        self.assertNotEqual(apellidos_raw, "Rodríguez")

        # Y deben ser strings base64 (Fernet token empieza con "gAAAAA")
        self.assertTrue(cedula_raw.startswith("gAAAAA"))
        self.assertTrue(nombres_raw.startswith("gAAAAA"))
        self.assertTrue(apellidos_raw.startswith("gAAAAA"))

    def test_cedula_hash_sigue_funcionando(self):
        p = crear_paciente(
            cedula="V-11111111",
            nombres="Test",
            apellidos="Hash",
            usuario=self.usuario,
        )
        encontrado = buscar_paciente_por_cedula("V-11111111")
        self.assertEqual(encontrado, p)
        # El hash se calculó sobre el plaintext, no sobre el ciphertext
        self.assertEqual(encontrado.cedula, "V-11111111")

    def test_datos_legacy_se_toleran(self):
        # Simular una fila con datos legacy en plaintext (pre-migración)
        p = crear_paciente(
            nombres="Legacy",
            apellidos="Test",
            usuario=self.usuario,
        )
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE pacientes_paciente "
                "SET nombres = %s, apellidos = %s "
                "WHERE id = %s",
                ["PlainOldName", "PlainOldLast", str(p.pk)],
            )
        # Leer desde el ORM: from_db_value debe tolerar InvalidToken
        p.refresh_from_db()
        # Tolerancia: devuelve el valor tal cual (no rompe)
        self.assertEqual(p.nombres, "PlainOldName")

    def test_actualizar_recifra_datos_legacy(self):
        p = crear_paciente(
            nombres="Viejo",
            apellidos="Plain",
            usuario=self.usuario,
        )
        # Insertar plaintext legacy
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE pacientes_paciente "
                "SET nombres = %s WHERE id = %s",
                ["ViejoPlain", str(p.pk)],
            )
        # Releer (tolerado), modificar, guardar → se cifra
        p.refresh_from_db()
        p.nombres = "NuevoCifrado"
        p.save()
        # Verificar que en BD ahora está cifrado
        with connection.cursor() as cur:
            cur.execute(
                "SELECT nombres FROM pacientes_paciente WHERE id = %s",
                [str(p.pk)],
            )
            raw = cur.fetchone()[0]
        self.assertTrue(raw.startswith("gAAAAA"))
        self.assertNotEqual(raw, "NuevoCifrado")
