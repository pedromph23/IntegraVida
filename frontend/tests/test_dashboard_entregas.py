"""Tests de F3.g.3 — Entregas UI (lista, detalle, dispatcher POST).

Lógica de estados + stock en apps.inventario.services, cubierta por
apps/inventario/tests_entregas.py. Aquí testeamos UI + dispatcher +
scope. Los constraint de Entrega: al menos un destino (hospital/refugio/
texto) y no ambos refugio+hospital.
"""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.inventario.models import (
    Almacen, DetalleEntrega, Entrega, Insumo, Lote, Stock,
)
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


def _mk_almacen(org, nombre):
    code = f"alm-{uuid.uuid4().hex[:8]}"
    return Almacen.objects.create(
        codigo=code, nombre=nombre,
        organizacion=org, activo=True,
    )


def _mk_hospital(org):
    from apps.hospitales.models import Hospital
    code = f"hosp-{uuid.uuid4().hex[:8]}"
    return Hospital.objects.create(
        codigo=code, nombre=f"Hospital {code}",
        tipo="HOSPITAL", nivel="NIVEL_I",
        organizacion=org, direccion="Calle test",
        estado_operativo="DISPONIBLE",
    )


def _mk_insumo():
    code = f"ins-{uuid.uuid4().hex[:8]}"
    return Insumo.objects.create(
        codigo=code, nombre=f"Insumo {code}",
        categoria="AGUA", unidad_medida="LITRO",
        stock_minimo_global=Decimal("0.000"),
        requiere_lote=True, requiere_vencimiento=False,
        activo=True,
    )


def _mk_lote(insumo):
    return Lote.objects.create(insumo=insumo, codigo=f"lot-{uuid.uuid4().hex[:6]}")


def _mk_entrega(origen, autor, estado="BORRADOR", hospital=None, destinatario_texto=""):
    return Entrega.objects.create(
        codigo=f"ent-{uuid.uuid4().hex[:8]}",
        almacen_origen=origen,
        hospital=hospital,
        destinatario_texto=destinatario_texto or ("" if hospital else "Destinatario test"),
        estado=estado,
        motivo="Motivo test", solicitada_por=autor,
    )


def _mk_detalle(e, insumo, lote, cantidad):
    return DetalleEntrega.objects.create(
        entrega=e, insumo=insumo, lote=lote,
        cantidad=cantidad,
        cantidad_entregada=Decimal("0.000"),
    )


class EntregasListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org_o = _mk_org()
        self.org_d = _mk_org()
        self.alm_o = _mk_almacen(self.org_o, "Origen")
        self.hosp = _mk_hospital(self.org_d)

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:entregas_list"))
        self.assertEqual(r.status_code, 302)

    def test_renders(self):
        r = self.client.get(reverse("dashboard:entregas_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Entregas")

    def test_shows_entrega(self):
        _mk_entrega(self.alm_o, self.admin, hospital=self.hosp)
        r = self.client.get(reverse("dashboard:entregas_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Hospital", table)

    def test_filters_by_estado(self):
        _mk_entrega(self.alm_o, self.admin, hospital=self.hosp, estado="BORRADOR")
        _mk_entrega(self.alm_o, self.admin, hospital=self.hosp, estado="ENVIADA")
        r = self.client.get(
            reverse("dashboard:entregas_list") + "?estado=ENVIADA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Enviada", table)
        self.assertNotIn("Borrador", table)

    def test_query_count_bounded(self):
        for _ in range(3):
            _mk_entrega(self.alm_o, self.admin, hospital=self.hosp)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:entregas_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 15,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class EntregaDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm_o = _mk_almacen(self.org, "Origen")
        self.hosp = _mk_hospital(self.org)
        self.insumo = _mk_insumo()
        self.lote = _mk_lote(self.insumo)
        self.e = _mk_entrega(self.alm_o, self.admin, hospital=self.hosp)
        _mk_detalle(self.e, self.insumo, self.lote, Decimal("10.000"))

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:entrega_detail", args=[self.e.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.e.codigo)

    def test_detail_404_otra_org(self):
        """Entrega real en OTRA org → 404."""
        u = _mk_user("cross_det_e")
        org_a = _mk_org()
        org_b = _mk_org()
        _mk_membresia(u, org_a)
        self.client.force_login(u)
        almacen_b = _mk_almacen(org_b, "AlmacenB")
        e_b = _mk_entrega(almacen_b, u)
        r = self.client.get(
            reverse("dashboard:entrega_detail", args=[e_b.id])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_404(self):
        r = self.client.get(
            reverse("dashboard:entrega_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_detalle(self):
        r = self.client.get(
            reverse("dashboard:entrega_detail", args=[self.e.id])
        )
        self.assertContains(r, self.insumo.nombre)

    def test_detail_shows_acciones_for_borrador(self):
        r = self.client.get(
            reverse("dashboard:entrega_detail", args=[self.e.id])
        )
        body = r.content.decode()
        self.assertIn("enviar", body.lower())


class EntregaAccionTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm_o = _mk_almacen(self.org, "Origen")
        self.hosp = _mk_hospital(self.org)
        self.insumo = _mk_insumo()
        self.lote = _mk_lote(self.insumo)
        self.e = _mk_entrega(self.alm_o, self.admin, hospital=self.hosp)
        self.url = reverse("dashboard:entrega_accion", args=[self.e.id])

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.post(self.url, {"accion": "enviar"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_accion_enviar_valid(self):
        # Stock suficiente en origen
        Stock.objects.create(
            almacen=self.alm_o, lote=self.lote,
            cantidad=Decimal("100.000"),
        )
        _mk_detalle(self.e, self.insumo, self.lote, Decimal("10.000"))
        r = self.client.post(self.url, {"accion": "enviar"})
        self.assertEqual(r.status_code, 302)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "ENVIADA")

    def test_accion_404_otra_org(self):
        """POST de acción cross-org → 404 y estado sin cambios."""
        u = _mk_user("cross_acc_e")
        org_a = _mk_org()
        org_b = _mk_org()
        _mk_membresia(u, org_a)
        self.client.force_login(u)
        almacen_b = _mk_almacen(org_b, "AlmacenB2")
        e_b = _mk_entrega(almacen_b, u)
        r = self.client.post(
            reverse("dashboard:entrega_accion", args=[e_b.id]),
            {"accion": "enviar"},
        )
        self.assertEqual(r.status_code, 404)
        e_b.refresh_from_db()
        self.assertEqual(e_b.estado, "BORRADOR")

    def test_accion_recibir_valid(self):
        """ENVIADA → RECIBIDA."""
        self.e.estado = "ENVIADA"
        self.e.save(update_fields=["estado"])
        _mk_detalle(self.e, self.insumo, self.lote, Decimal("10.000"))
        r = self.client.post(self.url, {"accion": "recibir"})
        self.assertEqual(r.status_code, 302)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "RECIBIDA")

    def test_accion_cancelar_enviada_valid(self):
        """ENVIADA → CANCELADA."""
        self.e.estado = "ENVIADA"
        self.e.save(update_fields=["estado"])
        _mk_detalle(self.e, self.insumo, self.lote, Decimal("10.000"))
        r = self.client.post(self.url, {"accion": "cancelar"})
        self.assertEqual(r.status_code, 302)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "CANCELADA")

    def test_accion_cancelar_borrador_valid(self):
        r = self.client.post(self.url, {"accion": "cancelar"})
        self.assertEqual(r.status_code, 302)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "CANCELADA")

    def test_accion_invalid_transition(self):
        # BORRADOR → recibir no permitida
        r = self.client.post(self.url, {"accion": "recibir"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "BORRADOR")

    def test_accion_unknown(self):
        r = self.client.post(self.url, {"accion": "volar"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, "BORRADOR")


class EntregaScopeTests(TestCase):
    def test_plain_user_sees_nothing(self):
        admin = _mk_superuser("admin")
        org = _mk_org()
        alm_o = _mk_almacen(org, "O")
        hosp = _mk_hospital(org)
        _mk_entrega(alm_o, admin, hospital=hosp)

        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:entregas_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("No hay entregas", table)

    def test_operator_sees_only_own_org(self):
        admin = _mk_superuser("admin")
        org1 = _mk_org()
        org2 = _mk_org()
        alm1 = _mk_almacen(org1, "Almacén UNO")
        alm2 = _mk_almacen(org2, "Almacén DOS")
        hosp2 = _mk_hospital(org2)

        # entrega A: origen alm1(org1) → hosp2(org2) → visible por org1
        # (el template muestra destino, no origen; verificamos por código)
        e_a = _mk_entrega(alm1, admin, hospital=hosp2)
        # entrega B: origen alm2(org2) → hosp2(org2) → solo visible por org2
        e_b = _mk_entrega(alm2, admin, hospital=hosp2)

        op = _mk_user("op")
        _mk_membresia(op, org1)
        self.client.force_login(op)
        r = self.client.get(reverse("dashboard:entregas_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        # A aparece (origen org1), B no (origen org2 y destino org2)
        self.assertIn(e_a.codigo, table)
        self.assertNotIn(e_b.codigo, table)
