#!/usr/bin/env python3
"""Fase 6.1.5 — tests + docs para portal de hospitales."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3

# ══════════════════════════════════════════════════════════════════
# Extender tests.py
# ══════════════════════════════════════════════════════════════════
tests_path = BASE / "apps" / "hospitales" / "tests.py"
existing = tests_path.read_text(encoding="utf-8")

nuevos = '''

# ══════════════════════════════════════════════════════════════════
# Portal público de hospitales (Fase 6.1.5)
# ══════════════════════════════════════════════════════════════════

from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from apps.hospitales.models import Servicio as ServicioModel


class PortalPublicoHospitalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(
            nombre="Org Portal",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="org-portal",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.disponible = Hospital.objects.create(
            codigo="pub-disp",
            nombre="Hospital Disponible",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III,
            organizacion=cls.org,
            direccion="Calle 1",
            estado_operativo=Hospital.EstadoOperativo.DISPONIBLE,
        )
        cls.saturado = Hospital.objects.create(
            codigo="pub-sat",
            nombre="Hospital Saturado",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_II,
            organizacion=cls.org,
            direccion="Calle 2",
            estado_operativo=Hospital.EstadoOperativo.SATURADO,
        )
        cls.colapsado = Hospital.objects.create(
            codigo="pub-col",
            nombre="Hospital Colapsado",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_IV,
            organizacion=cls.org,
            direccion="Calle 3",
            estado_operativo=Hospital.EstadoOperativo.COLAPSADO,
        )
        cls.no_op = Hospital.objects.create(
            codigo="pub-no",
            nombre="Hospital No Operativo",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_I,
            organizacion=cls.org,
            direccion="Calle 4",
            estado_operativo=Hospital.EstadoOperativo.NO_OPERATIVO,
        )

    def test_lista_anonima_200(self):
        r = self.client.get(reverse("hospitales:lista"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("resultados", r.json())

    def test_solo_estados_publicos(self):
        r = self.client.get(reverse("hospitales:lista"))
        codigos = {h["codigo"] for h in r.json()["resultados"]}
        self.assertIn("pub-disp", codigos)
        self.assertIn("pub-sat", codigos)
        self.assertNotIn("pub-col", codigos)
        self.assertNotIn("pub-no", codigos)

    def test_no_expone_campos_prohibidos(self):
        r = self.client.get(reverse("hospitales:lista"))
        primer = r.json()["resultados"][0]
        for campo in (
            "organizacion", "organizacion_id",
            "responsable", "responsable_id",
            "notas_internas",
        ):
            self.assertNotIn(campo, primer)

    def test_estructura_recursos_todos_los_tipos(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        recursos = r.json()["hospital"]["recursos"]
        for tipo in ("uci", "urgencia", "quirofano", "hospitalizacion"):
            self.assertIn(tipo, recursos)
            self.assertIn("estado", recursos[tipo])
            self.assertIn(
                recursos[tipo]["estado"],
                ("disponible", "no_disponible", "sin_datos"),
            )

    def test_sin_recurso_reporta_sin_datos(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.json()["hospital"]["recursos"]["uci"]["estado"], "sin_datos")

    def test_recurso_fresco_disponible(self):
        RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=3,
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.json()["hospital"]["recursos"]["uci"]["estado"], "disponible")

    def test_recurso_sin_disponibilidad(self):
        RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.URGENCIA,
            capacidad_total=20,
            disponible=0,
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(
            r.json()["hospital"]["recursos"]["urgencia"]["estado"],
            "no_disponible",
        )

    def test_recurso_desactualizado_sin_datos(self):
        r = RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.QUIROFANO,
            capacidad_total=5,
            disponible=2,
        )
        RecursoHospitalario.objects.filter(pk=r.pk).update(
            actualizado_en=timezone.now() - timedelta(hours=3)
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(
            r.json()["hospital"]["recursos"]["quirofano"]["estado"],
            "sin_datos",
        )

    def test_filtro_tipo_invalido_400(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"tipo": "INVALIDO"}
        )
        self.assertEqual(r.status_code, 400)

    def test_filtro_nivel(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"nivel": "NIVEL_III"}
        )
        self.assertEqual(r.status_code, 200)

    def test_filtro_estado_invalido_400(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"estado_operativo": "COLAPSADO"}
        )
        self.assertEqual(r.status_code, 400)

    def test_filtro_servicio(self):
        svc = ServicioModel.objects.create(
            codigo="test-svc-xyz",
            nombre="Servicio Test",
            tipo=ServicioModel.Tipo.SERVICIO,
        )
        HospitalServicio.objects.create(
            hospital=self.disponible, servicio=svc, disponible=True
        )
        r = self.client.get(
            reverse("hospitales:lista"), {"servicio": "test-svc-xyz"}
        )
        codigos = {h["codigo"] for h in r.json()["resultados"]}
        self.assertIn("pub-disp", codigos)
        self.assertNotIn("pub-sat", codigos)

    def test_detalle_activo_200(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["hospital"]["codigo"], "pub-disp")

    def test_detalle_colapsado_404(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-col"])
        )
        self.assertEqual(r.status_code, 404)

    def test_detalle_inexistente_404_identico_a_oculto(self):
        a = self.client.get(
            reverse("hospitales:detalle", args=["no-existe-xyz"])
        )
        b = self.client.get(
            reverse("hospitales:detalle", args=["pub-col"])
        )
        self.assertEqual(a.status_code, 404)
        self.assertEqual(b.status_code, 404)
        self.assertEqual(a.json(), b.json())

    def test_paginacion_offset(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"limite": 1, "offset": 1}
        )
        data = r.json()
        self.assertEqual(data["limite"], 1)
        self.assertEqual(data["offset"], 1)
        self.assertEqual(len(data["resultados"]), 1)


class CatalogoServiciosPrecargadosTests(TestCase):
    def test_servicios_comunes_existen(self):
        esperados = [
            "emergencia", "uci", "pediatria", "cardiologia",
            "cirugia_general", "quirofano", "hospitalizacion",
        ]
        for codigo in esperados:
            self.assertTrue(
                ServicioModel.objects.filter(codigo=codigo).exists(),
                f"Falta el servicio precargado: {codigo}",
            )
'''

if "class PortalPublicoHospitalesTests" not in existing:
    tests_path.write_text(existing + nuevos, encoding="utf-8")
    print("  OK: tests.py extendido (+16 tests)")
else:
    print("  ya aplicado: tests.py")

# ══════════════════════════════════════════════════════════════════
# Ampliar docs/api.md
# ══════════════════════════════════════════════════════════════════
api_doc = BASE / "docs" / "api.md"
text = api_doc.read_text(encoding="utf-8")

seccion = (
    "\n## Hospitales (Fase 6.1.5)\n\n"
    "### `GET /api/publico/hospitales/`\n\n"
    "Lista hospitales operativos públicos.\n\n"
    "**Estados expuestos:** `DISPONIBLE`, `SATURADO`.\n"
    "**Estados ocultos:** `COLAPSADO`, `NO_OPERATIVO` (§5.6: evitar pánico y\n"
    "desincentivar atención por vías alternativas).\n\n"
    "**Query params opcionales:**\n"
    "- `tipo`: HOSPITAL/CLINICA/CENTRO_SALUD/AMBULATORIO.\n"
    "- `nivel`: NIVEL_I/II/III/IV.\n"
    "- `estado_operativo`: solo DISPONIBLE o SATURADO (otros → 400).\n"
    "- `municipio`, `parroquia`: `icontains` por nombre.\n"
    "- `servicio`: código de servicio con `disponible=True` en ese hospital.\n"
    "- `q`: búsqueda en nombre/dirección.\n"
    "- `limite` (default 50), `offset` (default 0).\n\n"
    "**Campos NO expuestos:** `organizacion`, `responsable`, `notas_internas`.\n\n"
    "**Estructura de recursos** — cada tipo es un objeto con `estado` y `actualizado_en`:\n\n"
    + BT + "\n"
    "{\n"
    '  "uci": {"estado": "disponible", "actualizado_en": "2026-10-31T12:00:00-04:00"},\n'
    '  "urgencia": {"estado": "no_disponible", "actualizado_en": "..."},\n'
    '  "quirofano": {"estado": "sin_datos", "actualizado_en": null},\n'
    '  "hospitalizacion": {"estado": "disponible", "actualizado_en": "..."}\n'
    "}\n"
    + BT + "\n\n"
    "**Estados posibles por recurso:**\n"
    "- `disponible`: hay plazas y el dato fue actualizado hace < 2 h.\n"
    "- `no_disponible`: 0 plazas libres, actualizado recientemente.\n"
    "- `sin_datos`: sin registro, capacidad_total=0, o último dato > 2 h.\n\n"
    "**NO se publican números exactos** (ej. `3 camas UCI`) por §5.6:\n"
    "genera avalanchas y expectativas falsas si el dato no es fresco.\n\n"
    "### `GET /api/publico/hospitales/{codigo}/`\n\n"
    "Detalle por slug. 404 uniforme para inexistente o no público.\n"
)

if "## Hospitales (Fase 6.1.5)" not in text:
    api_doc.write_text(text.rstrip() + "\n" + seccion, encoding="utf-8")
    print("  OK: api.md ampliado con hospitales")
else:
    print("  ya aplicado: api.md")

print("\n✅ Tests y docs escritos. Ejecuta fase6_1_5_run.sh")
