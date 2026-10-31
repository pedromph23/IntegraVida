#!/usr/bin/env python3
"""Fase 5.5 — tests + docs para refugios públicos."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3

# ══════════════════════════════════════════════════════════════════
# 1) Extender apps/refugios/tests.py
# ══════════════════════════════════════════════════════════════════
print("== 1/2 tests.py ==")
tests_path = BASE / "apps" / "refugios" / "tests.py"
existing = tests_path.read_text(encoding="utf-8")

nuevos_tests = '''

# ══════════════════════════════════════════════════════════════════
# Portal público de refugios (Fase 5.5)
# ══════════════════════════════════════════════════════════════════

from django.urls import reverse


class PortalPublicoRefugiosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(
            nombre="Org Publica",
            tipo=Organizacion.Tipo.ONG,
            codigo="org-publica",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.activo = Refugio.objects.create(
            codigo="pub-activo",
            nombre="Refugio Activo",
            tipo=Refugio.Tipo.REFUGIO,
            organizacion=cls.org,
            direccion="Calle 1, Petare",
            capacidad_total=100,
            ocupacion_actual=30,
            estado_operativo=Refugio.EstadoOperativo.ACTIVO,
        )
        cls.lleno = Refugio.objects.create(
            codigo="pub-lleno",
            nombre="Refugio Lleno",
            tipo=Refugio.Tipo.REFUGIO,
            organizacion=cls.org,
            direccion="Calle 2, Catia",
            capacidad_total=50,
            ocupacion_actual=50,
            estado_operativo=Refugio.EstadoOperativo.LLENO,
        )
        cls.cerrado = Refugio.objects.create(
            codigo="pub-cerrado",
            nombre="Refugio Cerrado",
            tipo=Refugio.Tipo.REFUGIO,
            organizacion=cls.org,
            direccion="Calle 3",
            capacidad_total=100,
            ocupacion_actual=0,
            estado_operativo=Refugio.EstadoOperativo.CERRADO,
        )
        cls.mantenimiento = Refugio.objects.create(
            codigo="pub-mant",
            nombre="Refugio Mantenimiento",
            tipo=Refugio.Tipo.REFUGIO,
            organizacion=cls.org,
            direccion="Calle 4",
            capacidad_total=100,
            ocupacion_actual=0,
            estado_operativo=Refugio.EstadoOperativo.MANTENIMIENTO,
        )
        cls.inactivo = Refugio.objects.create(
            codigo="pub-inactivo",
            nombre="Refugio Inactivo",
            tipo=Refugio.Tipo.REFUGIO,
            organizacion=cls.org,
            direccion="Calle 5",
            capacidad_total=100,
            ocupacion_actual=0,
            estado_operativo=Refugio.EstadoOperativo.INACTIVO,
        )

    def test_lista_anonima_200(self):
        response = self.client.get(reverse("refugios:lista"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("resultados", data)
        self.assertIn("total", data)

    def test_solo_estados_publicos(self):
        response = self.client.get(reverse("refugios:lista"))
        codigos = {r["codigo"] for r in response.json()["resultados"]}
        self.assertIn("pub-activo", codigos)
        self.assertIn("pub-lleno", codigos)
        self.assertNotIn("pub-cerrado", codigos)
        self.assertNotIn("pub-mant", codigos)
        self.assertNotIn("pub-inactivo", codigos)

    def test_no_expone_campos_prohibidos(self):
        response = self.client.get(reverse("refugios:lista"))
        primer = response.json()["resultados"][0]
        for campo in (
            "organizacion",
            "organizacion_id",
            "responsable",
            "responsable_id",
            "notas_internas",
        ):
            self.assertNotIn(campo, primer)

    def test_filtro_municipio(self):
        response = self.client.get(
            reverse("refugios:lista"), {"municipio": "inexistente"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)

    def test_filtro_estado_invalido_400(self):
        response = self.client.get(
            reverse("refugios:lista"), {"estado_operativo": "CERRADO"}
        )
        self.assertEqual(response.status_code, 400)

    def test_filtro_q(self):
        response = self.client.get(reverse("refugios:lista"), {"q": "Petare"})
        codigos = {r["codigo"] for r in response.json()["resultados"]}
        self.assertIn("pub-activo", codigos)
        self.assertNotIn("pub-lleno", codigos)

    def test_detalle_activo_200(self):
        response = self.client.get(
            reverse("refugios:detalle", args=["pub-activo"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["refugio"]["codigo"], "pub-activo")

    def test_detalle_cerrado_404(self):
        response = self.client.get(
            reverse("refugios:detalle", args=["pub-cerrado"])
        )
        self.assertEqual(response.status_code, 404)

    def test_detalle_inexistente_404(self):
        r_inexistente = self.client.get(
            reverse("refugios:detalle", args=["no-existe-xyz"])
        )
        r_cerrado = self.client.get(
            reverse("refugios:detalle", args=["pub-cerrado"])
        )
        self.assertEqual(r_inexistente.status_code, 404)
        self.assertEqual(r_cerrado.status_code, 404)
        self.assertEqual(r_inexistente.json(), r_cerrado.json())

    def test_paginacion_offset(self):
        response = self.client.get(
            reverse("refugios:lista"), {"limite": 1, "offset": 1}
        )
        data = response.json()
        self.assertEqual(data["limite"], 1)
        self.assertEqual(data["offset"], 1)
        self.assertEqual(len(data["resultados"]), 1)


class OcupacionActualizadaEnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(
            nombre="Org Ocup",
            tipo=Organizacion.Tipo.ONG,
            codigo="org-ocup",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.refugio = Refugio.objects.create(
            codigo="pub-ocup",
            nombre="Refugio con historial",
            organizacion=cls.org,
            direccion="x",
            capacidad_total=100,
            ocupacion_actual=50,
            estado_operativo=Refugio.EstadoOperativo.ACTIVO,
        )

    def test_ocupacion_actualizada_en_null_si_no_hay_registros(self):
        response = self.client.get(
            reverse("refugios:detalle", args=["pub-ocup"])
        )
        self.assertIsNone(response.json()["refugio"]["ocupacion_actualizada_en"])

    def test_ocupacion_actualizada_en_presente_tras_registro(self):
        registrar_ocupacion(
            refugio_id=self.refugio.id,
            cantidad_nueva=60,
            usuario=None,
        )
        response = self.client.get(
            reverse("refugios:detalle", args=["pub-ocup"])
        )
        self.assertIsNotNone(response.json()["refugio"]["ocupacion_actualizada_en"])
'''

if "class PortalPublicoRefugiosTests" not in existing:
    tests_path.write_text(existing + nuevos_tests, encoding="utf-8")
    print("  OK: tests.py extendido (+12 tests)")
else:
    print("  ya aplicado: tests.py")

# ══════════════════════════════════════════════════════════════════
# 2) Ampliar docs/api.md
# ══════════════════════════════════════════════════════════════════
print("== 2/2 docs/api.md ==")
api_doc = BASE / "docs" / "api.md"
text = api_doc.read_text(encoding="utf-8")

seccion = (
    "\n## Refugios (Fase 5.5)\n\n"
    "### `GET /api/publico/refugios/`\n\n"
    "Lista refugios operativos públicos.\n\n"
    "**Estados expuestos:** `ACTIVO`, `LLENO`.\n"
    "**Estados ocultos:** `MANTENIMIENTO`, `CERRADO`, `INACTIVO` (§5.5).\n\n"
    "**Query params opcionales:**\n"
    "- `tipo`: valor de `Refugio.Tipo`.\n"
    "- `estado_operativo`: solo `ACTIVO` o `LLENO` (otros → 400).\n"
    "- `municipio`: `icontains` por nombre.\n"
    "- `parroquia`: `icontains` por nombre.\n"
    "- `q`: búsqueda en `nombre` o `direccion` (máx 100 chars).\n"
    "- `limite` (default 50): 1–100.\n"
    "- `offset` (default 0): entero >= 0.\n\n"
    "**Campos NO expuestos:** `organizacion`, `responsable`, `notas_internas`.\n\n"
    "**Respuesta 200:**\n\n"
    + BT + "\n"
    "{\n"
    '  "total": 5,\n'
    '  "limite": 50,\n'
    '  "offset": 0,\n'
    '  "resultados": [\n'
    "    {\n"
    '      "id": "uuid",\n'
    '      "codigo": "refugio-petare-1",\n'
    '      "nombre": "...",\n'
    '      "tipo": "REFUGIO",\n'
    '      "tipo_texto": "Refugio",\n'
    '      "direccion": "...",\n'
    '      "referencia_lugar": "",\n'
    '      "punto": {"latitud": 10.5, "longitud": -66.9},\n'
    '      "municipio": "Sucre",\n'
    '      "parroquia": "Petare",\n'
    '      "capacidad_total": 100,\n'
    '      "capacidad_disponible": 70,\n'
    '      "porcentaje_ocupacion": 30.0,\n'
    '      "esta_lleno": false,\n'
    '      "servicios": ["agua", "cocina"],\n'
    '      "estado_operativo": "ACTIVO",\n'
    '      "estado_operativo_texto": "Activo",\n'
    '      "telefono_publico": "...",\n'
    '      "correo_publico": "",\n'
    '      "ocupacion_actualizada_en": "2026-10-31T12:00:00-04:00"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    + BT + "\n\n"
    "`ocupacion_actualizada_en` es `null` si el refugio no ha tenido cambios "
    "de ocupación desde su creación.\n\n"
    "### `GET /api/publico/refugios/{codigo}/`\n\n"
    "Detalle por `codigo` (slug único).\n\n"
    "**200:** `{\"refugio\": {...}}` con los mismos campos del listado.\n\n"
    "**404:** si no existe o no está en estado público. La respuesta es\n"
    "idéntica en ambos casos (no filtra existencia).\n"
)

if "## Refugios (Fase 5.5)" not in text:
    api_doc.write_text(text.rstrip() + "\n" + seccion, encoding="utf-8")
    print("  OK: docs/api.md ampliado con refugios")
else:
    print("  ya aplicado: docs/api.md")

print("\n✅ Tests y docs escritos. Ejecuta scripts/fase5_5_run.sh")
