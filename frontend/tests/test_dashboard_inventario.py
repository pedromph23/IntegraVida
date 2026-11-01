"""Tests de F3.g.1 — Inventario lectura (Insumo, Almacen, Lote, Stock, Movimiento).

La lógica de movimientos vive en apps.inventario.services (cubierta por
apps/inventario/tests*.py). Aquí testeamos UI de lectura + ámbito por
membresía + alerta bajo stock + kardex.
"""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.inventario.models import Almacen, Insumo, Lote, Movimiento, Stock
from apps.organizaciones.models import Membresia, Organizacion

User = get_user_model()


def _mk_superuser(username):
    return User.objects.create_superuser(username=username, password="x")


def _mk_user(username):
    return User.objects.create_user(username=username, password="x")


def _mk_org():
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=f"Org {code}", codigo=code,
        tipo="OTRO" if "OTRO" in tipos else (tipos[0] if tipos else "OTRO"),
        estado="ACTIVA" if "ACTIVA" in estados else (estados[0] if estados else "ACTIVA"),
    )


def _mk_membresia(user, org):
    rol_f = Membresia._meta.get_field("rol")
    roles = [c[0] for c in rol_f.choices] if rol_f.choices else []
    rol = "OPERADOR" if "OPERADOR" in roles else (roles[0] if roles else "")
    return Membresia.objects.create(
        usuario=user, organizacion=org,
        rol=rol, estado=Membresia.Estado.ACTIVA,
    )


def _mk_almacen(org, nombre="Almacén test"):
    code = f"alm-{uuid.uuid4().hex[:8]}"
    return Almacen.objects.create(
        codigo=code, nombre=nombre,
        organizacion=org, activo=True,
    )


def _mk_insumo(nombre="Agua potable", stock_minimo=Decimal("50.000")):
    code = f"ins-{uuid.uuid4().hex[:8]}"
    return Insumo.objects.create(
        codigo=code, nombre=nombre,
        categoria="AGUA", unidad_medida="LITRO",
        stock_minimo_global=stock_minimo,
        requiere_lote=True, requiere_vencimiento=True,
        activo=True,
    )


def _mk_lote(insumo, fecha_vencimiento=None):
    code = f"lot-{uuid.uuid4().hex[:8]}"
    return Lote.objects.create(
        insumo=insumo, codigo=code,
        fecha_vencimiento=fecha_vencimiento,
    )


def _mk_stock(almacen, lote, cantidad):
    return Stock.objects.create(
        almacen=almacen, lote=lote, cantidad=cantidad,
    )


class InsumosListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm = _mk_almacen(self.org)

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:insumos_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_renders(self):
        r = self.client.get(reverse("dashboard:insumos_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Insumos")

    def test_shows_insumo(self):
        ins = _mk_insumo(nombre="Arroz")
        r = self.client.get(reverse("dashboard:insumos_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn(ins.codigo, table)

    def test_filters_by_categoria(self):
        _mk_insumo(nombre="AguaX")
        r = self.client.get(
            reverse("dashboard:insumos_list") + "?categoria=MEDICINA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertNotIn("AguaX", table)
        self.assertIn("No hay insumos", table)

    def test_filters_by_bajo_stock(self):
        # insumo con stock mínimo 100 y 0 stock → bajo
        _mk_insumo(nombre="InsumoBajo", stock_minimo=Decimal("100.000"))
        # insumo con stock mínimo 0 → nunca bajo
        _mk_insumo(nombre="InsumoNormal", stock_minimo=Decimal("0.000"))
        r = self.client.get(
            reverse("dashboard:insumos_list") + "?bajo_stock=true"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("InsumoBajo", table)
        self.assertNotIn("InsumoNormal", table)


class InsumoDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm = _mk_almacen(self.org, "Central")
        self.insumo = _mk_insumo(stock_minimo=Decimal("50.000"))
        self.lote = _mk_lote(self.insumo)
        self.stock = _mk_stock(self.alm, self.lote, Decimal("10.000"))

    def test_renders(self):
        r = self.client.get(
            reverse("dashboard:insumo_detail", args=[self.insumo.codigo])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.insumo.nombre)

    def test_404(self):
        r = self.client.get(
            reverse("dashboard:insumo_detail", args=["nope"])
        )
        self.assertEqual(r.status_code, 404)

    def test_shows_stocks(self):
        r = self.client.get(
            reverse("dashboard:insumo_detail", args=[self.insumo.codigo])
        )
        self.assertContains(r, "Central")
        self.assertContains(r, self.lote.codigo)


class StockListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm = _mk_almacen(self.org)
        self.insumo = _mk_insumo(stock_minimo=Decimal("50.000"))
        self.lote = _mk_lote(self.insumo)
        self.stock = _mk_stock(self.alm, self.lote, Decimal("10.000"))

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:stock_list"))
        self.assertEqual(r.status_code, 302)

    def test_renders(self):
        r = self.client.get(reverse("dashboard:stock_list"))
        self.assertEqual(r.status_code, 200)

    def test_bajo_stock_filter(self):
        # segundo stock con cantidad > mínimo
        lote2 = _mk_lote(self.insumo)
        _mk_stock(self.alm, lote2, Decimal("200.000"))
        r = self.client.get(
            reverse("dashboard:stock_list") + "?bajo_stock=true"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn(self.lote.codigo, table)
        self.assertNotIn(lote2.codigo, table)

    def test_query_count_bounded(self):
        _mk_lote(self.insumo)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:stock_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 15,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class StockDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm = _mk_almacen(self.org)
        self.insumo = _mk_insumo()
        self.lote = _mk_lote(self.insumo)
        self.stock = _mk_stock(self.alm, self.lote, Decimal("10.000"))

    def test_renders(self):
        r = self.client.get(
            reverse("dashboard:stock_detail", args=[self.stock.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.insumo.nombre)

    def test_404_unknown(self):
        r = self.client.get(
            reverse("dashboard:stock_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_shows_kardex(self):
        Movimiento.objects.create(
            stock=self.stock, tipo="ENTRADA",
            cantidad=Decimal("10.000"),
            cantidad_anterior=Decimal("0.000"),
            cantidad_nueva=Decimal("10.000"),
            diferencia=Decimal("10.000"),
            registrado_por=self.admin,
        )
        r = self.client.get(
            reverse("dashboard:stock_detail", args=[self.stock.id])
        )
        self.assertContains(r, "Entrada")


class ScopeTests(TestCase):
    def test_plain_user_sees_no_stock(self):
        admin = _mk_superuser("admin")
        org = _mk_org()
        alm = _mk_almacen(org)
        ins = _mk_insumo()
        lote = _mk_lote(ins)
        _mk_stock(alm, lote, Decimal("10.000"))

        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:stock_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("No hay stock", table)

    def test_operator_sees_only_own_org(self):
        admin = _mk_superuser("admin")
        org1 = _mk_org()
        org2 = _mk_org()
        alm1 = _mk_almacen(org1, "Almacén 1")
        alm2 = _mk_almacen(org2, "Almacén 2")
        ins = _mk_insumo()
        lote1 = _mk_lote(ins)
        lote2 = _mk_lote(ins)
        _mk_stock(alm1, lote1, Decimal("10.000"))
        _mk_stock(alm2, lote2, Decimal("20.000"))

        op = _mk_user("op")
        _mk_membresia(op, org1)
        self.client.force_login(op)
        r = self.client.get(reverse("dashboard:stock_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Almacén 1", table)
        self.assertNotIn("Almacén 2", table)
