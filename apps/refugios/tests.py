from django.contrib.auth import get_user_model
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
