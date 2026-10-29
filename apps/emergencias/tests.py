import json

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from apps.emergencias.models import Emergencia


class ListaEmergenciasPublicasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.confirmada = Emergencia.objects.create(
            titulo="Inundacion confirmada",
            descripcion="Calle principal anegada",
            categoria=Emergencia.Categoria.INUNDACION,
            gravedad=Emergencia.Gravedad.ALTA,
            estado=Emergencia.Estado.CONFIRMADA,
            ubicacion_texto="Petare, Caracas",
        )
        cls.en_atencion = Emergencia.objects.create(
            titulo="Incendio en atencion",
            descripcion="Galpon en llamas",
            categoria=Emergencia.Categoria.INCENDIO,
            gravedad=Emergencia.Gravedad.CRITICA,
            estado=Emergencia.Estado.EN_ATENCION,
            ubicacion_texto="Catia, Caracas",
        )
        cls.resuelta = Emergencia.objects.create(
            titulo="Derrumbe resuelto",
            descripcion="Via despejada",
            categoria=Emergencia.Categoria.DESLIZAMIENTO,
            gravedad=Emergencia.Gravedad.MODERADA,
            estado=Emergencia.Estado.RESUELTA,
            ubicacion_texto="El Junquito, Caracas",
        )
        cls.recibida = Emergencia.objects.create(
            titulo="Reporte sin verificar",
            descripcion="Aun no confirmado",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.RECIBIDA,
            ubicacion_texto="Desconocido",
        )
        cls.en_verificacion = Emergencia.objects.create(
            titulo="En verificacion",
            descripcion="Verificando",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.EN_VERIFICACION,
            ubicacion_texto="Desconocido",
        )
        cls.descartada = Emergencia.objects.create(
            titulo="Descartada",
            descripcion="Falsa alarma",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.DESCARTADA,
            ubicacion_texto="Desconocido",
        )

    def test_lista_anonima_devuelve_200(self):
        response = self.client.get(reverse("emergencias:lista"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("resultados", data)
        self.assertIn("total", data)

    def test_solo_estados_publicos(self):
        response = self.client.get(reverse("emergencias:lista"))
        ids = {r["id"] for r in response.json()["resultados"]}
        self.assertIn(str(self.confirmada.id), ids)
        self.assertIn(str(self.en_atencion.id), ids)
        self.assertIn(str(self.resuelta.id), ids)
        self.assertNotIn(str(self.recibida.id), ids)
        self.assertNotIn(str(self.en_verificacion.id), ids)
        self.assertNotIn(str(self.descartada.id), ids)

    def test_no_expone_campos_prohibidos(self):
        response = self.client.get(reverse("emergencias:lista"))
        primer = response.json()["resultados"][0]
        for campo_prohibido in (
            "reportada_por",
            "reportada_por_id",
            "organizacion",
            "organizacion_id",
        ):
            self.assertNotIn(campo_prohibido, primer)

    def test_detalle_verificado_devuelve_200(self):
        url = reverse("emergencias:detalle", args=[self.confirmada.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("emergencia", response.json())

    def test_detalle_no_verificado_devuelve_404(self):
        for emergencia in (self.recibida, self.en_verificacion, self.descartada):
            url = reverse("emergencias:detalle", args=[emergencia.id])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("emergencia", response.json())

    def test_paginacion_offset(self):
        response = self.client.get(
            reverse("emergencias:lista"),
            {"limite": 1, "offset": 1},
        )
        data = response.json()
        self.assertEqual(data["limite"], 1)
        self.assertEqual(data["offset"], 1)
        self.assertEqual(len(data["resultados"]), 1)


class CrearReportePublicoTests(TestCase):
    def setUp(self):
        cache.clear()

    def _payload_valido(self):
        return {
            "descripcion": "Calle inundada",
            "ubicacion_texto": "Caracas",
            "categoria": "INUNDACION",
        }

    def test_post_sin_csrf_funciona(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("emergencias:crear-reporte"),
            data=json.dumps(self._payload_valido()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("reporte_id", response.json())
        self.assertEqual(response.json()["estado_revision"], "PENDIENTE")

    def test_post_con_charset_utf8_funciona(self):
        response = self.client.post(
            reverse("emergencias:crear-reporte"),
            data=json.dumps(self._payload_valido()),
            content_type="application/json; charset=utf-8",
        )
        self.assertEqual(response.status_code, 201)

    def test_post_campos_prohibidos_400(self):
        payload = self._payload_valido()
        payload["campo_extra"] = "no permitido"
        response = self.client.post(
            reverse("emergencias:crear-reporte"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_sin_categoria_400(self):
        payload = self._payload_valido()
        del payload["categoria"]
        response = self.client.post(
            reverse("emergencias:crear-reporte"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_no_permitido(self):
        response = self.client.get(reverse("emergencias:crear-reporte"))
        self.assertEqual(response.status_code, 405)


class EstadoServicioTests(TestCase):
    def test_estado_servicio_reportes(self):
        response = self.client.get(reverse("emergencias:estado-servicio"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["disponible"])
        self.assertEqual(data["servicio"], "recepcion_reportes")
