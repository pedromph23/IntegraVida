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
