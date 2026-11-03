"""Tests de F3.h.1 — Reportes (UI wrapper de apps.reportes.services).

La generación de datos + auditoría de RegistroExportacion está cubierta
por apps/reportes/tests.py. Aquí testeamos:
- Listado de reportes disponibles
- POST ejecuta el servicio y crea RegistroExportacion
- Historial con filtros y scope
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.organizaciones.models import Membresia, Organizacion
from apps.reportes.models import RegistroExportacion

User = get_user_model()


def _mk_superuser(username):
    return User.objects.create_superuser(username=username, password="x")


def _mk_user(username):
    return User.objects.create_user(username=username, password="x")


def _mk_org(nombre=None):
    tipo_f = Organizacion._meta.get_field("tipo")
    estado_f = Organizacion._meta.get_field("estado")
    tipos = [c[0] for c in tipo_f.choices] if tipo_f.choices else []
    estados = [c[0] for c in estado_f.choices] if estado_f.choices else []
    code = f"org-{uuid.uuid4().hex[:8]}"
    return Organizacion.objects.create(
        nombre=nombre or f"Org {code}", codigo=code,
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


class ReportesIndexTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:reportes_index"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_renders_catalogo(self):
        r = self.client.get(reverse("dashboard:reportes_index"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Inventario crítico", body)
        self.assertIn("Capacidad operativa", body)

    def test_link_a_historial(self):
        r = self.client.get(reverse("dashboard:reportes_index"))
        self.assertContains(r, reverse("dashboard:reportes_historial"))


class ReporteEjecutarTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org("Org Reportes")
        # Los servicios de reportes exigen acceso explícito a la organización
        # (tiene_acceso_a_organizacion no exime al superuser).
        _mk_membresia(self.admin, self.org)

    def test_slug_invalido_404(self):
        r = self.client.get(
            reverse("dashboard:reporte_ejecutar", args=["no-existe"])
        )
        self.assertEqual(r.status_code, 404)

    def test_get_muestra_form(self):
        r = self.client.get(
            reverse("dashboard:reporte_ejecutar", args=["inventario-critico"])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "<form")
        self.assertContains(r, "Inventario crítico")

    def test_post_org_ajena_no_crea_registro(self):
        """POST con organizacion ajena → error, no crea registro, no ejecuta servicio."""
        op = _mk_user("op_ajeno")
        org_a = _mk_org("OrgA_ajena_test")
        org_b = _mk_org("OrgB_ajena_test")
        _mk_membresia(op, org_a)
        self.client.force_login(op)
        before = RegistroExportacion.objects.count()
        r = self.client.post(
            reverse("dashboard:reporte_ejecutar", args=["inventario-critico"]),
            {"organizacion": str(org_b.id)},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            RegistroExportacion.objects.count(), before,
            "POST con org ajena NO debe crear RegistroExportacion",
        )
        self.assertNotContains(
            r, "Resultado (JSON)",
            msg_prefix="Servicio no debe ejecutarse con org ajena",
        )
        self.assertContains(r, "Organización inválida")

    def test_post_user_sin_membresias_no_crea_registro(self):
        """User autenticado sin membresías → sin registro, sin ejecutar servicio."""
        u = _mk_user("no_memb_reportes")
        self.client.force_login(u)
        before = RegistroExportacion.objects.count()
        r = self.client.post(
            reverse("dashboard:reporte_ejecutar", args=["inventario-critico"]),
            {},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RegistroExportacion.objects.count(), before)
        self.assertNotContains(r, "Resultado (JSON)")

    def test_post_inventario_registra_exportacion(self):
        before = RegistroExportacion.objects.count()
        r = self.client.post(
            reverse("dashboard:reporte_ejecutar", args=["inventario-critico"]),
            {},
        )
        self.assertEqual(r.status_code, 200)
        after = RegistroExportacion.objects.count()
        self.assertGreater(after, before, "El POST debe crear RegistroExportacion")
        # Y debe haber JSON renderizado
        self.assertContains(r, "Resultado (JSON)")

    def test_post_capacidad_registra_exportacion(self):
        before = RegistroExportacion.objects.count()
        r = self.client.post(
            reverse("dashboard:reporte_ejecutar", args=["capacidad-operativa"]),
            {},
        )
        self.assertEqual(r.status_code, 200)
        after = RegistroExportacion.objects.count()
        self.assertGreater(after, before)


class HistorialTests(TestCase):
    def setUp(self):
        self.admin = _mk_superuser("admin")
        self.client.force_login(self.admin)
        self.org = _mk_org()

    def test_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:reportes_historial"))
        self.assertEqual(r.status_code, 302)

    def test_renders_vacio(self):
        r = self.client.get(reverse("dashboard:reportes_historial"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Historial")

    def test_lists_exportaciones(self):
        RegistroExportacion.objects.create(
            usuario=self.admin, organizacion=self.org,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=3,
            archivo_ruta="", resultado="EXITOSO", detalle="OK",
        )
        r = self.client.get(reverse("dashboard:reportes_historial"))
        self.assertContains(r, "Inventario crítico")
        self.assertContains(r, "Exitoso")

    def test_filters_by_contenido(self):
        for contenido in ("INVENTARIO_CRITICO", "CAPACIDAD_OPERATIVA"):
            RegistroExportacion.objects.create(
                usuario=self.admin, organizacion=self.org,
                tipo="JSON", contenido=contenido,
                parametros={}, filas_incluidas=0,
                archivo_ruta="", resultado="EXITOSO", detalle="",
            )
        r = self.client.get(
            reverse("dashboard:reportes_historial")
            + "?contenido=CAPACIDAD_OPERATIVA"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Capacidad operativa", table)
        self.assertNotIn("Inventario crítico", table)

    def test_filters_by_resultado(self):
        RegistroExportacion.objects.create(
            usuario=self.admin, organizacion=self.org,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=0,
            archivo_ruta="", resultado="EXITOSO", detalle="",
        )
        RegistroExportacion.objects.create(
            usuario=self.admin, organizacion=self.org,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=0,
            archivo_ruta="", resultado="ERROR", detalle="Falla",
        )
        r = self.client.get(
            reverse("dashboard:reportes_historial") + "?resultado=ERROR"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Error", table)

    def test_query_count_bounded(self):
        for _ in range(3):
            RegistroExportacion.objects.create(
                usuario=self.admin, organizacion=self.org,
                tipo="JSON", contenido="INVENTARIO_CRITICO",
                parametros={}, filas_incluidas=0,
                archivo_ruta="", resultado="EXITOSO", detalle="",
            )
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:reportes_historial"))
        self.assertLessEqual(
            len(ctx.captured_queries), 15,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )


class HistorialScopeTests(TestCase):
    def test_historial_admin_ve_todo(self):
        """Admin de plataforma ve exportaciones de TODAS las orgs."""
        admin = _mk_superuser("admin_hist")
        org1 = _mk_org("HistOrg1")
        org2 = _mk_org("HistOrg2")
        RegistroExportacion.objects.create(
            usuario=admin, organizacion=org1,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="A",
        )
        RegistroExportacion.objects.create(
            usuario=admin, organizacion=org2,
            tipo="JSON", contenido="CAPACIDAD_OPERATIVA",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="B",
        )
        self.client.force_login(admin)
        r = self.client.get(reverse("dashboard:reportes_historial"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Inventario crítico", table)
        self.assertIn("Capacidad operativa", table)

    def test_operator_sees_only_own_org_exportaciones(self):
        admin = _mk_superuser("admin")
        org1 = _mk_org("Org1")
        org2 = _mk_org("Org2")
        # exportación de org1
        RegistroExportacion.objects.create(
            usuario=admin, organizacion=org1,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="X",
        )
        # exportación de org2
        RegistroExportacion.objects.create(
            usuario=admin, organizacion=org2,
            tipo="JSON", contenido="CAPACIDAD_OPERATIVA",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="Y",
        )

        op = _mk_user("op")
        _mk_membresia(op, org1)
        self.client.force_login(op)
        r = self.client.get(reverse("dashboard:reportes_historial"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Inventario crítico", table)
        self.assertNotIn("Capacidad operativa", table)


    def test_historial_exportacion_personal_sin_org_visible(self):
        """Exportación personal (organizacion=None) propia visible, ajena no."""
        u = _mk_user("personal_hist")
        org_a = _mk_org("OrgPersonal")
        _mk_membresia(u, org_a)
        RegistroExportacion.objects.create(
            usuario=u, organizacion=None,
            tipo="JSON", contenido="INVENTARIO_CRITICO",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="personal",
        )
        otro = _mk_user("otro_personal_hist")
        RegistroExportacion.objects.create(
            usuario=otro, organizacion=None,
            tipo="JSON", contenido="CAPACIDAD_OPERATIVA",
            parametros={}, filas_incluidas=1,
            archivo_ruta="", resultado="EXITOSO", detalle="ajena",
        )
        self.client.force_login(u)
        r = self.client.get(reverse("dashboard:reportes_historial"))
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("Inventario crítico", table)
        self.assertNotIn("Capacidad operativa", table)
