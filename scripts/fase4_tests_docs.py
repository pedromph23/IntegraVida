#!/usr/bin/env python3
"""Escribe tests de §18.1 y docs/api.md. Idempotente."""
from pathlib import Path
import sys

BASE = Path.cwd()
BT = chr(96) * 3   # ``` para Markdown
B1 = chr(96)       # ` simple

if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def write(path, content):
    p = BASE / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"escrito: {path} ({len(content)} chars)")

# ══════════════════════════════════════════════════════════════════
# tests.py
# ══════════════════════════════════════════════════════════════════
tests = '''import json

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
'''

write("apps/emergencias/tests.py", tests)

# ══════════════════════════════════════════════════════════════════
# docs/api.md
# ══════════════════════════════════════════════════════════════════
api_doc = (
    "# API de IntegraVida — Contrato publico\n\n"
    "> **Estado:** parcial — cubre los endpoints publicos de emergencias.\n"
    "> El resto de la API se documentara al cierre de su fase.\n\n"
    "## Base URL (desarrollo)\n\n"
    + BT + "\nhttp://127.0.0.1:8000/api/publico/\n" + BT + "\n\n"
    "## Autenticacion\n\n"
    "**Ningun endpoint publico requiere autenticacion ni cookies.**\n"
    "Los endpoints internos (`/api/interno/...`) si requieren sesion.\n\n"
    "## Justificacion de `@csrf_exempt` en endpoints publicos\n\n"
    "`POST /api/publico/emergencias/reportes/` recibe JSON sin que exista\n"
    "sesion previa. No hay cookies reutilizables para CSRF. El rate limiting\n"
    "por IP (§6.4) es la defensa aplicable. Los endpoints internos NO son\n"
    "`csrf_exempt`.\n\n"
    "## Endpoints\n\n"
    "### `GET /api/publico/emergencias/`\n\n"
    "Lista eventos en estado publico.\n\n"
    "**Query params opcionales:**\n"
    "- `categoria`: valor de `Emergencia.Categoria`.\n"
    "- `gravedad`: 1, 2, 3 o 4.\n"
    "- `municipio`: busqueda `icontains`.\n"
    "- `q`: busqueda en `ubicacion_texto` o `titulo`.\n"
    "- `limite` (default 50): 1–100.\n"
    "- `offset` (default 0): entero >= 0.\n\n"
    "**Estados expuestos:** `CONFIRMADA`, `EN_ATENCION`, `RESUELTA`.\n\n"
    "**Estados ocultos:** `RECIBIDA`, `EN_VERIFICACION`, `DESCARTADA` (§5.4, §6.4).\n\n"
    "**Campos NO expuestos:** `reportada_por`, `organizacion` (§6.2, §11).\n\n"
    "### `GET /api/publico/emergencias/{uuid}/`\n\n"
    "Detalle de una emergencia publica.\n\n"
    "**200:** `{\"emergencia\": {...}}`\n\n"
    "**404:** si no existe o no esta en estado publico (no filtra existencia).\n\n"
    "### `POST /api/publico/emergencias/reportes/`\n\n"
    "Recibe un reporte ciudadano anonimo. Queda `PENDIENTE`.\n\n"
    "**Content-Type:** `application/json` (acepta `; charset=utf-8`).\n\n"
    "**Campos permitidos:** `descripcion`, `ubicacion_texto`, `categoria`, `referencia_lugar`.\n\n"
    "**Respuesta 201:**\n\n"
    + BT + "\n"
    '{\n  "mensaje": "Reporte recibido. Quedara pendiente de verificacion.",\n'
    '  "reporte_id": "uuid",\n  "estado_revision": "PENDIENTE"\n}\n'
    + BT + "\n\n"
    "**Errores:** 400 (validacion), 415 (content-type), 429 (rate limit 5/min por IP).\n\n"
    "### `GET /api/publico/emergencias/reportes/estado/`\n\n"
    "Ping publico del servicio.\n\n"
    + BT + "\n"
    '{"servicio": "recepcion_reportes", "disponible": true}\n'
    + BT + "\n\n"
    "## Codigos HTTP\n\n"
    "| Codigo | Significado |\n|---|---|\n"
    "| 200 | OK |\n| 201 | Recurso creado |\n| 400 | Solicitud invalida |\n"
    "| 404 | No encontrado o no publico |\n| 405 | Metodo no permitido |\n"
    "| 415 | Content-Type incorrecto |\n| 429 | Rate limit excedido |\n"
)

write("docs/api.md", api_doc)

print("\n✅ Tests y docs escritos. Ejecuta scripts/fase4_run.sh")
