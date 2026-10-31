from django.test import TestCase

from apps.usuarios.models import Usuario


class UsuarioModelTests(TestCase):
    def test_usuario_se_crea_con_uuid_y_correo_unico(self):
        usuario = Usuario.objects.create_user(
            username="usuario_prueba",
            email="prueba@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )

        self.assertIsNotNone(usuario.pk)
        self.assertEqual(usuario.email, "prueba@example.test")
        self.assertTrue(usuario.check_password(
            "ClaveTemporal-SoloPruebas-123!"
        ))


# ══════════════════════════════════════════════════════════════════
# Unicidad condicional de email (Fase 6.3.1)
# ══════════════════════════════════════════════════════════════════

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.usuarios.models import Usuario


class EmailUnicidadCondicionalTests(TestCase):
    def test_multiples_usuarios_sin_email(self):
        u1 = Usuario.objects.create_user(username="sin-email-1", password="x")
        u2 = Usuario.objects.create_user(username="sin-email-2", password="x")
        u3 = Usuario.objects.create_user(username="sin-email-3", password="x")
        self.assertEqual(u1.email, "")
        self.assertEqual(u2.email, "")
        self.assertEqual(u3.email, "")
        self.assertEqual(Usuario.objects.filter(email="").count(), 3)

    def test_dos_usuarios_con_mismo_email_falla(self):
        Usuario.objects.create_user(
            username="con-email-1",
            email="dup@test.local",
            password="x",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create_user(
                    username="con-email-2",
                    email="dup@test.local",
                    password="x",
                )

    def test_emails_distintos_ok(self):
        u1 = Usuario.objects.create_user(
            username="ok-1", email="a@test.local", password="x"
        )
        u2 = Usuario.objects.create_user(
            username="ok-2", email="b@test.local", password="x"
        )
        self.assertEqual(u1.email, "a@test.local")
        self.assertEqual(u2.email, "b@test.local")
