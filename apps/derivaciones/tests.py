from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.derivaciones.models import Derivacion, TransicionEstado
from apps.derivaciones.services import (
    solicitar_derivacion,
    transicionar_derivacion,
)
from apps.hospitales.models import Hospital
from apps.organizaciones.models import Membresia, Organizacion
from apps.pacientes.models import Episodio
from apps.pacientes.services import crear_paciente
from apps.triaje.models import Triaje
from apps.triaje.services import registrar_triaje

Usuario = get_user_model()


def _setup(slug):
    org = Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.HOSPITAL,
        codigo=f"org-{slug}",
        estado=Organizacion.Estado.ACTIVA,
    )
    h_origen = Hospital.objects.create(
        codigo=f"h-o-{slug}",
        nombre="H Origen",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="x",
    )
    h_destino = Hospital.objects.create(
        codigo=f"h-d-{slug}",
        nombre="H Destino",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="y",
    )
    usuario = Usuario.objects.create_user(
        username=f"u-{slug}",
        email=f"u-{slug}@test.local",
        password="x",
    )
    Membresia.objects.create(
        usuario=usuario,
        organizacion=org,
        rol=Membresia.Rol.SANITARIO,
        estado=Membresia.Estado.ACTIVA,
    )
    paciente = crear_paciente(
        nombres="Paciente", apellidos="Deriv", usuario=usuario
    )
    episodio = Episodio.objects.create(
        paciente=paciente,
        hospital=h_origen,
        motivo_consulta="Fractura",
        registrado_por=usuario,
    )
    return org, h_origen, h_destino, usuario, episodio


class DerivacionModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        (cls.org, cls.h_origen, cls.h_destino,
         cls.usuario, cls.episodio) = _setup("m")

    def test_crear_valida(self):
        d = Derivacion.objects.create(
            episodio=self.episodio,
            hospital_origen=self.h_origen,
            hospital_destino=self.h_destino,
            motivo="x",
            solicitada_por=self.usuario,
        )
        self.assertEqual(d.estado, Derivacion.Estado.SOLICITADA)
        self.assertEqual(d.prioridad, Derivacion.Prioridad.MEDIA)

    def test_origen_igual_destino_falla(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Derivacion.objects.create(
                    episodio=self.episodio,
                    hospital_origen=self.h_origen,
                    hospital_destino=self.h_origen,
                    motivo="x",
                    solicitada_por=self.usuario,
                )


class SolicitarDerivacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        (cls.org, cls.h_origen, cls.h_destino,
         cls.usuario, cls.episodio) = _setup("s")

    def test_solicitar_valida(self):
        d = solicitar_derivacion(
            episodio_id=self.episodio.pk,
            hospital_destino=self.h_destino,
            motivo="Requiere UCI",
            prioridad=Derivacion.Prioridad.ALTA,
            usuario=self.usuario,
        )
        self.assertEqual(d.estado, Derivacion.Estado.SOLICITADA)
        self.assertEqual(TransicionEstado.objects.count(), 1)

    def test_motivo_vacio_falla(self):
        with self.assertRaises(ValidationError):
            solicitar_derivacion(
                episodio_id=self.episodio.pk,
                hospital_destino=self.h_destino,
                motivo="   ",
                usuario=self.usuario,
            )

    def test_prioridad_menor_que_triaje_falla(self):
        registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.ROJO,
            usuario=self.usuario,
        )
        with self.assertRaises(ValidationError):
            solicitar_derivacion(
                episodio_id=self.episodio.pk,
                hospital_destino=self.h_destino,
                motivo="x",
                prioridad=Derivacion.Prioridad.BAJA,
                usuario=self.usuario,
            )

    def test_prioridad_mayor_que_triaje_ok(self):
        registrar_triaje(
            episodio_id=self.episodio.pk,
            clasificacion=Triaje.Clasificacion.VERDE,
            usuario=self.usuario,
        )
        d = solicitar_derivacion(
            episodio_id=self.episodio.pk,
            hospital_destino=self.h_destino,
            motivo="x",
            prioridad=Derivacion.Prioridad.CRITICA,
            usuario=self.usuario,
        )
        self.assertEqual(d.prioridad, Derivacion.Prioridad.CRITICA)

    def test_sin_acceso_falla(self):
        otro = Usuario.objects.create_user(
            username="ajeno",
            email="ajeno@test.local",
            password="x",
        )
        with self.assertRaises(PermissionDenied):
            solicitar_derivacion(
                episodio_id=self.episodio.pk,
                hospital_destino=self.h_destino,
                motivo="x",
                usuario=otro,
            )

    def test_destino_igual_origen_falla(self):
        with self.assertRaises(ValidationError):
            solicitar_derivacion(
                episodio_id=self.episodio.pk,
                hospital_destino=self.h_origen,
                motivo="x",
                usuario=self.usuario,
            )

    def test_audita_solicitud(self):
        solicitar_derivacion(
            episodio_id=self.episodio.pk,
            hospital_destino=self.h_destino,
            motivo="x",
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="derivacion.solicitada"
            ).count(),
            1,
        )


class TransicionarDerivacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        (cls.org, cls.h_origen, cls.h_destino,
         cls.usuario, cls.episodio) = _setup("t")

    def _crear(self):
        return solicitar_derivacion(
            episodio_id=self.episodio.pk,
            hospital_destino=self.h_destino,
            motivo="x",
            usuario=self.usuario,
        )

    def test_flujo_completo(self):
        d = self._crear()
        for estado in (
            Derivacion.Estado.ACEPTADA,
            Derivacion.Estado.ASIGNADA,
            Derivacion.Estado.EN_CAMINO,
            Derivacion.Estado.COMPLETADA,
        ):
            transicionar_derivacion(
                derivacion_id=d.pk, nuevo_estado=estado,
                usuario=self.usuario,
            )
        d.refresh_from_db()
        self.assertEqual(d.estado, Derivacion.Estado.COMPLETADA)
        self.assertIsNotNone(d.aceptada_en)
        self.assertIsNotNone(d.iniciada_en)
        self.assertIsNotNone(d.completada_en)
        self.assertEqual(d.aceptada_por, self.usuario)
        self.assertEqual(TransicionEstado.objects.count(), 5)

    def test_salto_invalido_falla(self):
        d = self._crear()
        with self.assertRaises(ValidationError):
            transicionar_derivacion(
                derivacion_id=d.pk,
                nuevo_estado=Derivacion.Estado.COMPLETADA,
                usuario=self.usuario,
            )

    def test_terminal_no_permite_cambios(self):
        d = self._crear()
        transicionar_derivacion(
            derivacion_id=d.pk,
            nuevo_estado=Derivacion.Estado.RECHAZADA,
            usuario=self.usuario,
        )
        with self.assertRaises(ValidationError):
            transicionar_derivacion(
                derivacion_id=d.pk,
                nuevo_estado=Derivacion.Estado.ACEPTADA,
                usuario=self.usuario,
            )

    def test_audita_cada_transicion(self):
        d = self._crear()
        antes = EventoAuditoria.objects.filter(
            accion="derivacion.transicion"
        ).count()
        transicionar_derivacion(
            derivacion_id=d.pk,
            nuevo_estado=Derivacion.Estado.ACEPTADA,
            usuario=self.usuario,
        )
        despues = EventoAuditoria.objects.filter(
            accion="derivacion.transicion"
        ).count()
        self.assertEqual(despues, antes + 1)
