#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/reportes/admin.py << 'EOF'
from django.contrib import admin

from apps.reportes.models import RegistroExportacion


@admin.register(RegistroExportacion)
class RegistroExportacionAdmin(admin.ModelAdmin):
    list_display = (
        "contenido", "usuario", "organizacion", "tipo",
        "resultado", "filas_incluidas", "creado_en",
    )
    list_filter = ("contenido", "tipo", "resultado")
    search_fields = ("usuario__username", "detalle")
    readonly_fields = (
        "id", "usuario", "organizacion", "tipo", "contenido",
        "parametros", "filas_incluidas", "archivo_ruta",
        "tamano_bytes", "resultado", "detalle", "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
EOF

cat > apps/reportes/tests.py << 'EOF'
"""Tests de Fase 9.1 — reportes operativos."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.derivaciones.models import Derivacion
from apps.hospitales.models import Hospital
from apps.inventario.models import Almacen, Insumo, Lote, Stock
from apps.organizaciones.models import Membresia, Organizacion
from apps.reportes.models import RegistroExportacion
from apps.reportes.services import (
    generar_reporte_capacidad_operativa,
    generar_reporte_inventario_critico,
)
from apps.refugios.models import Refugio

Usuario = get_user_model()


def _org(slug):
    return Organizacion.objects.create(
        nombre=f"Org {slug}", tipo=Organizacion.Tipo.ONG,
        codigo=f"org-{slug}", estado=Organizacion.Estado.ACTIVA,
    )


class BaseReportesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("rep")
        cls.user = Usuario.objects.create_user(
            username="rep-u", email="rep-u@test.local", password="x",
        )
        Membresia.objects.create(
            usuario=cls.user, organizacion=cls.org,
            rol=Membresia.Rol.COORDINADOR, estado=Membresia.Estado.ACTIVA,
        )
        cls.hospital = Hospital.objects.create(
            codigo="h-rep", nombre="H", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org,
            direccion="x",
        )
        cls.almacen = Almacen.objects.create(
            codigo="alm-rep", nombre="A", organizacion=cls.org,
            hospital=cls.hospital,
        )
        cls.insumo = Insumo.objects.create(
            codigo="ins-rep", nombre="Medicina",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True, requiere_vencimiento=True,
            stock_minimo_global=Decimal("20"),
        )
        cls.lote_cerca = Lote.objects.create(
            insumo=cls.insumo, codigo="L-CERCA",
            fecha_vencimiento=date.today() + timedelta(days=10),
        )
        cls.lote_vencido = Lote.objects.create(
            insumo=cls.insumo, codigo="L-VEN",
            fecha_vencimiento=date.today() - timedelta(days=5),
        )
        cls.lote_ok = Lote.objects.create(
            insumo=cls.insumo, codigo="L-OK",
            fecha_vencimiento=date.today() + timedelta(days=365),
        )
        Stock.objects.create(
            almacen=cls.almacen, lote=cls.lote_cerca, cantidad=Decimal("5"),
        )
        Stock.objects.create(
            almacen=cls.almacen, lote=cls.lote_vencido, cantidad=Decimal("2"),
        )
        Stock.objects.create(
            almacen=cls.almacen, lote=cls.lote_ok, cantidad=Decimal("50"),
        )
        cls.refugio = Refugio.objects.create(
            codigo="ref-rep", nombre="R", organizacion=cls.org,
            direccion="y", capacidad_total=100, ocupacion_actual=80,
            estado_operativo=Refugio.EstadoOperativo.ACTIVO,
        )


class InventarioCriticoTests(BaseReportesTest):
    def test_reporte_detecta_insumo_bajo_minimo(self):
        data = generar_reporte_inventario_critico(
            usuario=self.user, organizacion=self.org,
        )
        # Total stock = 5+2+50 = 57, mínimo 20 → NO bajo mínimo
        self.assertEqual(len(data["insumos_bajo_minimo"]), 0)

    def test_reporte_detecta_lote_por_vencer(self):
        data = generar_reporte_inventario_critico(
            usuario=self.user, organizacion=self.org,
        )
        self.assertEqual(len(data["lotes_por_vencer"]), 1)
        self.assertEqual(data["lotes_por_vencer"][0]["lote_codigo"], "L-CERCA")

    def test_reporte_detecta_lote_vencido(self):
        data = generar_reporte_inventario_critico(
            usuario=self.user, organizacion=self.org,
        )
        self.assertEqual(len(data["lotes_vencidos"]), 1)
        self.assertEqual(data["lotes_vencidos"][0]["lote_codigo"], "L-VEN")

    def test_registra_exportacion(self):
        antes = RegistroExportacion.objects.count()
        generar_reporte_inventario_critico(
            usuario=self.user, organizacion=self.org,
        )
        self.assertEqual(RegistroExportacion.objects.count(), antes + 1)
        r = RegistroExportacion.objects.latest("creado_en")
        self.assertEqual(
            r.contenido, RegistroExportacion.Contenido.INVENTARIO_CRITICO,
        )

    def test_sin_acceso_falla(self):
        otro_user = Usuario.objects.create_user(
            username="ajeno", email="ajeno@test.local", password="x",
        )
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            generar_reporte_inventario_critico(
                usuario=otro_user, organizacion=self.org,
            )


class CapacidadOperativaTests(BaseReportesTest):
    def test_reporte_incluye_refugios(self):
        data = generar_reporte_capacidad_operativa(
            usuario=self.user, organizacion=self.org,
        )
        self.assertEqual(len(data["refugios"]), 1)
        self.assertEqual(data["refugios"][0]["capacidad_disponible"], 20)
        self.assertEqual(data["refugios"][0]["porcentaje_ocupacion"], 80.0)

    def test_reporte_cuenta_hospitales_por_estado(self):
        data = generar_reporte_capacidad_operativa(
            usuario=self.user, organizacion=self.org,
        )
        self.assertIn("DISPONIBLE", data["hospitales_por_estado"])


class EndpointTests(BaseReportesTest):
    def test_anonimo_401(self):
        r = self.client.get(reverse("reportes:inventario-critico"))
        self.assertEqual(r.status_code, 401)

    def test_autenticado_sin_org_ok(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("reportes:inventario-critico"))
        self.assertEqual(r.status_code, 200)

    def test_autenticado_con_org_ok(self):
        self.client.force_login(self.user)
        r = self.client.get(
            reverse("reportes:inventario-critico"),
            {"organizacion": str(self.org.pk)},
        )
        self.assertEqual(r.status_code, 200)

    def test_org_inexistente_400(self):
        self.client.force_login(self.user)
        r = self.client.get(
            reverse("reportes:inventario-critico"),
            {"organizacion": "00000000-0000-0000-0000-000000000000"},
        )
        self.assertEqual(r.status_code, 400)

    def test_capacidad_endpoint_200(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("reportes:capacidad-operativa"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("refugios", r.json())
EOF

echo "OK: admin + 12 tests"

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations reportes
python3 manage.py migrate reportes

echo ""
echo "▶ Tests reportes"
python3 manage.py test apps.reportes -v 2

echo ""
echo "▶ Regresión completa"
python3 manage.py test apps.inventario apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 9.1 COMPLETADA"
