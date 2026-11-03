"""Tests de F3.g.2 — Transferencias UI (lista, detalle, dispatcher POST).

La lógica de estados + stock vive en apps.inventario.services y está
cubierta por apps/inventario/tests_transferencias.py. Aquí testeamos:
- Render de lista/detalle con ámbito
- Que el POST despacha al servicio correcto
- Errores de transición inválida se muestran al usuario
"""
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.inventario.models import (
    Almacen, DetalleTransferencia, Insumo, Lote, Stock, Transferencia,
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


def _mk_transferencia(origen, destino, autor, estado="BORRADOR", prioridad="MEDIA"):
    return Transferencia.objects.create(
        codigo=f"tr-{uuid.uuid4().hex[:8]}",
        almacen_origen=origen, almacen_destino=destino,
        prioridad=prioridad, estado=estado,
        motivo="Motivo test", solicitada_por=autor,
    )


def _mk_detalle(t, insumo, lote, cantidad):
    return DetalleTransferencia.objects.create(
        transferencia=t, insumo=insumo, lote_origen=lote,
        cantidad=cantidad,
        cantidad_despachada=Decimal("0.000"),
        cantidad_recibida=Decimal("0.000"),
    )


class TransferenciasListTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org_o = _mk_org()
        self.org_d = _mk_org()
        self.alm_o = _mk_almacen(self.org_o, "Origen")
        self.alm_d = _mk_almacen(self.org_d, "Destino")

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:transferencias_list"))
        self.assertEqual(r.status_code, 302)

    def test_renders(self):
        r = self.client.get(reverse("dashboard:transferencias_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Transferencias")

    def test_shows_transferencia(self):
        _mk_transferencia(self.alm_o, self.alm_d, self.admin)
        r = self.client.get(reverse("dashboard:transferencias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Origen", table)

    def test_filters_by_estado(self):
        _mk_transferencia(self.alm_o, self.alm_d, self.admin, estado="BORRADOR")
        _mk_transferencia(self.alm_o, self.alm_d, self.admin, estado="RECIBIDA")
        r = self.client.get(
            reverse("dashboard:transferencias_list") + "?estado=RECIBIDA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Recibida", table)
        self.assertNotIn("Borrador", table)

    def test_query_count_bounded(self):
        for _ in range(3):
            _mk_transferencia(self.alm_o, self.alm_d, self.admin)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:transferencias_list"))
        self.assertLessEqual(
            len(ctx.captured_queries), 15,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class TransferenciaDetailTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm_o = _mk_almacen(self.org, "Origen")
        self.alm_d = _mk_almacen(self.org, "Destino")
        self.insumo = _mk_insumo()
        self.lote = _mk_lote(self.insumo)
        self.t = _mk_transferencia(self.alm_o, self.alm_d, self.admin)
        _mk_detalle(self.t, self.insumo, self.lote, Decimal("10.000"))

    def test_detail_renders(self):
        r = self.client.get(
            reverse("dashboard:transferencia_detail", args=[self.t.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.t.codigo)

    def test_detail_404_otra_org(self):
        """Transferencia real en OTRA org → 404."""
        u = _mk_user("cross_det_t")
        org_a = _mk_org()
        org_b = _mk_org()
        org_c = _mk_org()
        _mk_membresia(u, org_a)
        self.client.force_login(u)
        alm_b = _mk_almacen(org_b, "AlmB")
        alm_c = _mk_almacen(org_c, "AlmC")
        t_bc = _mk_transferencia(alm_b, alm_c, u)
        r = self.client.get(
            reverse("dashboard:transferencia_detail", args=[t_bc.id])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_404(self):
        r = self.client.get(
            reverse("dashboard:transferencia_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_detail_shows_detalle(self):
        r = self.client.get(
            reverse("dashboard:transferencia_detail", args=[self.t.id])
        )
        self.assertContains(r, self.insumo.nombre)
        self.assertContains(r, self.lote.codigo)

    def test_detail_shows_acciones_for_borrador(self):
        r = self.client.get(
            reverse("dashboard:transferencia_detail", args=[self.t.id])
        )
        body = r.content.decode()
        # Debe haber "aprobar" como opción
        self.assertIn("aprobar", body.lower())


class TransferenciaAccionTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()
        self.alm_o = _mk_almacen(self.org, "Origen")
        self.alm_d = _mk_almacen(self.org, "Destino")
        self.insumo = _mk_insumo()
        self.lote = _mk_lote(self.insumo)
        self.t = _mk_transferencia(self.alm_o, self.alm_d, self.admin)
        self.url = reverse(
            "dashboard:transferencia_accion", args=[self.t.id],
        )

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.post(self.url, {"accion": "aprobar"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_get_rejected(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_accion_aprobar_valid(self):
        r = self.client.post(self.url, {"accion": "aprobar"})
        self.assertEqual(r.status_code, 302)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "APROBADA")

    def test_accion_rechazar_valid(self):
        r = self.client.post(self.url, {"accion": "rechazar"})
        self.assertEqual(r.status_code, 302)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "RECHAZADA")

    def test_accion_despachar_valid(self):
        # Aprobar primero
        self.t.estado = "APROBADA"
        self.t.save(update_fields=["estado"])
        # Crear stock en origen suficiente
        Stock.objects.create(
            almacen=self.alm_o, lote=self.lote,
            cantidad=Decimal("100.000"),
        )
        _mk_detalle(self.t, self.insumo, self.lote, Decimal("10.000"))

        r = self.client.post(self.url, {"accion": "despachar"})
        self.assertEqual(r.status_code, 302)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "EN_TRANSITO")

    def test_accion_404_otra_org(self):
        """POST cross-org → 404 y estado sin cambios."""
        u = _mk_user("cross_acc_t")
        org_a = _mk_org()
        org_b = _mk_org()
        org_c = _mk_org()
        _mk_membresia(u, org_a)
        self.client.force_login(u)
        alm_b = _mk_almacen(org_b, "AlmB2")
        alm_c = _mk_almacen(org_c, "AlmC2")
        t_bc = _mk_transferencia(alm_b, alm_c, u)
        r = self.client.post(
            reverse("dashboard:transferencia_accion", args=[t_bc.id]),
            {"accion": "aprobar"},
        )
        self.assertEqual(r.status_code, 404)
        t_bc.refresh_from_db()
        self.assertEqual(t_bc.estado, "BORRADOR")

    def test_accion_recibir_valid(self):
        """EN_TRANSITO → RECIBIDA."""
        self.t.estado = "EN_TRANSITO"
        self.t.save(update_fields=["estado"])
        det = _mk_detalle(self.t, self.insumo, self.lote, Decimal("10.000"))
        det.cantidad_despachada = Decimal("10.000")
        det.save(update_fields=["cantidad_despachada"])
        r = self.client.post(self.url, {"accion": "recibir"})
        self.assertEqual(r.status_code, 302)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "RECIBIDA")

    def test_accion_cancelar_borrador_valid(self):
        """BORRADOR → CANCELADA."""
        r = self.client.post(self.url, {"accion": "cancelar"})
        self.assertEqual(r.status_code, 302)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "CANCELADA")

    def test_accion_invalid_transition(self):
        # BORRADOR → recibir no permitida
        r = self.client.post(self.url, {"accion": "recibir"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "BORRADOR")

    def test_accion_unknown(self):
        r = self.client.post(self.url, {"accion": "volar"}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.t.refresh_from_db()
        self.assertEqual(self.t.estado, "BORRADOR")


class TransferenciaScopeTests(TestCase):
    def test_plain_user_sees_nothing(self):
        admin = _mk_superuser("admin")
        org = _mk_org()
        alm_o = _mk_almacen(org, "O")
        alm_d = _mk_almacen(org, "D")
        _mk_transferencia(alm_o, alm_d, admin)

        plain = _mk_user("plain")
        self.client.force_login(plain)
        r = self.client.get(reverse("dashboard:transferencias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("No hay transferencias", table)

    def test_operator_sees_only_own_org(self):
        admin = _mk_superuser("admin")
        org1 = _mk_org()
        org2 = _mk_org()
        alm1 = _mk_almacen(org1, "Almacén UNO")
        alm2 = _mk_almacen(org2, "Almacén DOS")
        alm3 = _mk_almacen(org2, "Almacén TRES")
        _mk_transferencia(alm1, alm2, admin)   # cruza org1 → org2
        _mk_transferencia(alm3, alm2, admin)   # solo org2

        op = _mk_user("op")
        _mk_membresia(op, org1)
        self.client.force_login(op)
        r = self.client.get(reverse("dashboard:transferencias_list"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        # La primera cruza org1, la ve
        self.assertIn("Almacén UNO", table)
        # La segunda solo org2, no la ve
        self.assertNotIn("Almacén TRES", table)
