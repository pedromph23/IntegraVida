"""Tests de F4.d — Auditoría del admin custom.

Solo lectura. Filtros (resultado, actor, accion, tipo_objeto, fechas),
paginación, detalle con hash chain + metadatos, guard staff/superuser,
headers anti-index.
"""
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.usuarios.services import enroll_admin_mfa


User = get_user_model()


def _mk_superuser(username="admin", password="test-pass-123!"):
    return User.objects.create_superuser(username=username, password=password)


def _mk_plain(username="plain", password="test-pass-123!"):
    return User.objects.create_user(username=username, password=password)


def _mfa_session(client, user):
    s = client.session
    s["admin_mfa_verified_at"] = timezone.now().timestamp()
    s["admin_mfa_user_id"] = str(user.pk)
    s.save()


def _mk_evento(
    actor,
    accion="test.accion",
    resultado="EXITOSO",
    tipo_objeto="Test",
    objeto_id="",
    metadatos=None,
):
    # hash_anterior y hash_actual son unique → uuid por evento
    return EventoAuditoria.objects.create(
        actor=actor,
        accion=accion,
        tipo_objeto=tipo_objeto,
        objeto_id=objeto_id,
        resultado=resultado,
        justificacion="Test",
        direccion_ip="127.0.0.1",
        agente_usuario="test-agent/1.0",
        id_correlacion="",
        metadatos=metadatos or {},
        hash_anterior=uuid.uuid4().hex,
        hash_actual=uuid.uuid4().hex,
    )


@override_settings(ADMIN_MFA_REQUIRED=True)
class AuditAnonimoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG

    def test_anonimo_va_a_login_admin(self):
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(f"/{self.slug}/login/", r["Location"])
        self.assertNotIn("/panel/login/", r["Location"])


@override_settings(ADMIN_MFA_REQUIRED=True)
class AuditNoStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_plain("plain_audit")
        self.client = Client()
        self.client.login(username="plain_audit", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_no_staff_403_list(self):
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        self.assertEqual(r.status_code, 403)

    def test_no_staff_403_detail(self):
        # Crear evento (no importa quién lo creó)
        admin = _mk_superuser("owner_admin")
        ev = _mk_evento(admin)
        r = self.client.get(
            reverse("admin_custom:admin_audit_detail", args=[ev.id])
        )
        self.assertEqual(r.status_code, 403)


@override_settings(ADMIN_MFA_REQUIRED=True)
class AuditListStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_superuser("audit_admin")
        enroll_admin_mfa(self.user)
        self.client = Client()
        self.client.login(username="audit_admin", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_renders_200(self):
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Auditoría")

    def test_sin_eventos_vacio(self):
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        self.assertContains(r, "Sin eventos registrados")

    def test_con_eventos_muestra_tabla(self):
        _mk_evento(self.user, accion="login.exitoso", resultado="EXITOSO")
        _mk_evento(self.user, accion="accion.denegada", resultado="DENEGADO")
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        body = r.content.decode()
        self.assertIn("login.exitoso", body)
        self.assertIn("accion.denegada", body)
        self.assertIn("Exitoso", body)
        self.assertIn("Denegado", body)

    def test_filtro_por_resultado(self):
        _mk_evento(self.user, accion="ok.accion", resultado="EXITOSO")
        _mk_evento(self.user, accion="den.accion", resultado="DENEGADO")
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + "?resultado=DENEGADO"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("den.accion", table)
        self.assertNotIn("ok.accion", table)

    def test_filtro_por_actor(self):
        otro = _mk_superuser("otro_admin")
        _mk_evento(self.user, accion="mio.accion")
        _mk_evento(otro, accion="ajeno.accion")
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + "?actor=audit_admin"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("mio.accion", table)
        self.assertNotIn("ajeno.accion", table)

    def test_filtro_por_accion(self):
        _mk_evento(self.user, accion="login.exitoso")
        _mk_evento(self.user, accion="admin.transicion")
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + "?accion=login"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("login.exitoso", table)
        self.assertNotIn("admin.transicion", table)

    def test_filtro_por_tipo_objeto(self):
        _mk_evento(self.user, accion="ev1", tipo_objeto="Usuario")
        _mk_evento(self.user, accion="ev2", tipo_objeto="Refugio")
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + "?tipo_objeto=Usuario"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertIn("ev1", table)
        self.assertNotIn("ev2", table)

    def test_filtro_desde(self):
        # Evento de hoy → aparece con desde=hoy (fecha LOCAL, no UTC,
        # para evitar falsos negativos cuando UTC ya cambió de día).
        _mk_evento(self.user, accion="hoy.evento")
        hoy_local = timezone.localtime(timezone.now()).date().isoformat()
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + f"?desde={hoy_local}"
        )
        self.assertContains(r, "hoy.evento")

    def test_filtro_hasta_excluye_futuro(self):
        # Los eventos son inmutables (update() bloqueado). Creamos un
        # evento HOY y filtramos hasta=AYER (fecha LOCAL): debe quedar
        # fuera.
        from datetime import timedelta
        _mk_evento(self.user, accion="evento.hoy")
        ayer_local = (
            timezone.localtime(timezone.now()).date() - timedelta(days=1)
        ).isoformat()
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + f"?hasta={ayer_local}"
        )
        body = r.content.decode()
        table = body.split("<table", 1)[1].split("</table>", 1)[0]
        self.assertNotIn("evento.hoy", table)

    def test_fecha_invalida_ignorada(self):
        _mk_evento(self.user, accion="visible.evento")
        r = self.client.get(
            reverse("admin_custom:admin_audit_list") + "?desde=xyz"
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "visible.evento")

    def test_headers_anti_index(self):
        r = self.client.get(reverse("admin_custom:admin_audit_list"))
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertIn("no-store", r.get("Cache-Control", ""))


@override_settings(ADMIN_MFA_REQUIRED=True)
class AuditDetailStaffTests(TestCase):
    def setUp(self):
        self.user = _mk_superuser("detail_admin")
        enroll_admin_mfa(self.user)
        self.client = Client()
        self.client.login(username="detail_admin", password="test-pass-123!")
        _mfa_session(self.client, self.user)

    def test_renders_200_con_evento(self):
        ev = _mk_evento(
            self.user, accion="detail.accion",
            metadatos={"foo": "bar", "num": 42},
        )
        r = self.client.get(
            reverse("admin_custom:admin_audit_detail", args=[ev.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "detail.accion")
        # Metadatos pretty-printed
        self.assertContains(r, "&quot;foo&quot;")
        self.assertContains(r, "&quot;bar&quot;")

    def test_404_unknown(self):
        r = self.client.get(
            reverse("admin_custom:admin_audit_detail", args=[uuid.uuid4()])
        )
        self.assertEqual(r.status_code, 404)

    def test_muestra_hash_chain(self):
        ev = _mk_evento(self.user)
        r = self.client.get(
            reverse("admin_custom:admin_audit_detail", args=[ev.id])
        )
        body = r.content.decode()
        self.assertIn("hash_anterior", body)
        self.assertIn("hash_actual", body)
        self.assertIn(ev.hash_actual, body)

    def test_headers_anti_index(self):
        ev = _mk_evento(self.user)
        r = self.client.get(
            reverse("admin_custom:admin_audit_detail", args=[ev.id])
        )
        self.assertEqual(r["X-Robots-Tag"], "noindex, nofollow, noarchive")
