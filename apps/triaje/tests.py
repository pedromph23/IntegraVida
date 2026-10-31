from django.contrib.auth import get_user_model
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
    usuario = Usuario.objects.create_user(
        username="triage-u", email="triage-u@test.local", password="x"
    )
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
            username="triage-ajeno", email="triage-ajeno@test.local",
            password="x"
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
