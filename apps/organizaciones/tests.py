from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.usuarios.models import Usuario
from apps.organizaciones.models import Organizacion, Membresia


class MembresiaModelTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="operador_prueba",
            email="operador@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )
        self.organizacion = Organizacion.objects.create(
            nombre="Organización de prueba",
            tipo=Organizacion.Tipo.ONG,
            codigo="organizacion-prueba",
        )

    def test_membresia_pendiente_se_crea_correctamente(self):
        membresia = Membresia.objects.create(
            usuario=self.usuario,
            organizacion=self.organizacion,
            rol=Membresia.Rol.OPERADOR,
        )

        self.assertEqual(membresia.estado, Membresia.Estado.PENDIENTE)
        self.assertEqual(membresia.usuario, self.usuario)
        self.assertEqual(membresia.organizacion, self.organizacion)

    def test_no_se_permite_dos_membresias_del_mismo_usuario(
        self,
    ):
        Membresia.objects.create(
            usuario=self.usuario,
            organizacion=self.organizacion,
            rol=Membresia.Rol.OPERADOR,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membresia.objects.create(
                    usuario=self.usuario,
                    organizacion=self.organizacion,
                    rol=Membresia.Rol.COORDINADOR,
                )


class PoliticaAccesoOrganizacionTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="operador_acceso",
            email="operador-acceso@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )
        self.organizacion = Organizacion.objects.create(
            nombre="Hospital de prueba",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="hospital-prueba-acceso",
            estado=Organizacion.Estado.ACTIVA,
        )
        self.membresia = Membresia.objects.create(
            usuario=self.usuario,
            organizacion=self.organizacion,
            rol=Membresia.Rol.OPERADOR,
            estado=Membresia.Estado.ACTIVA,
        )

    def test_miembro_activo_puede_acceder(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.assertTrue(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_membresia_pendiente_no_concede_acceso(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.membresia.estado = Membresia.Estado.PENDIENTE
        self.membresia.save(update_fields=["estado"])

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_membresia_suspendida_no_concede_acceso(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.membresia.estado = Membresia.Estado.SUSPENDIDA
        self.membresia.save(update_fields=["estado"])

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_membresia_revocada_no_concede_acceso(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.membresia.estado = Membresia.Estado.REVOCADA
        self.membresia.save(update_fields=["estado"])

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_usuario_inactivo_no_puede_acceder(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_organizacion_suspendida_no_concede_acceso_operativo(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.organizacion.estado = Organizacion.Estado.SUSPENDIDA
        self.organizacion.save(update_fields=["estado"])

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, self.organizacion)
        )

    def test_no_puede_acceder_a_otra_organizacion_sin_membresia(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        otra = Organizacion.objects.create(
            nombre="ONG diferente",
            tipo=Organizacion.Tipo.ONG,
            codigo="ong-diferente-acceso",
            estado=Organizacion.Estado.ACTIVA,
        )

        self.assertFalse(
            tiene_acceso_a_organizacion(self.usuario, otra)
        )

    def test_puede_restringir_acceso_por_rol(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.assertTrue(
            tiene_acceso_a_organizacion(
                self.usuario,
                self.organizacion,
                roles_permitidos=[Membresia.Rol.OPERADOR],
            )
        )
        self.assertFalse(
            tiene_acceso_a_organizacion(
                self.usuario,
                self.organizacion,
                roles_permitidos=[Membresia.Rol.SANITARIO],
            )
        )

    def test_lista_de_roles_vacia_deniega_acceso(self):
        from apps.organizaciones.services import tiene_acceso_a_organizacion

        self.assertFalse(
            tiene_acceso_a_organizacion(
                self.usuario,
                self.organizacion,
                roles_permitidos=[],
            )
        )

    def test_superusuario_global_se_verifica_por_separado(self):
        from apps.organizaciones.services import (
            puede_administrar_plataforma,
            tiene_acceso_a_organizacion,
        )

        administrador = Usuario.objects.create_superuser(
            username="admin_plataforma_prueba",
            email="admin-plataforma@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )

        self.assertTrue(puede_administrar_plataforma(administrador))
        self.assertFalse(
            tiene_acceso_a_organizacion(administrador, self.organizacion)
        )


class OrganizacionesInternasAPITests(TestCase):
    def setUp(self):
        self.url = "/api/interno/organizaciones/"

        self.usuario = Usuario.objects.create_user(
            username="usuario_api_org",
            email="usuario-api-org@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )
        self.organizacion_propia = Organizacion.objects.create(
            nombre="Hospital propio API",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="hospital-propio-api",
            estado=Organizacion.Estado.ACTIVA,
        )
        self.organizacion_ajena = Organizacion.objects.create(
            nombre="ONG ajena API",
            tipo=Organizacion.Tipo.ONG,
            codigo="ong-ajena-api",
            estado=Organizacion.Estado.ACTIVA,
        )
        Membresia.objects.create(
            usuario=self.usuario,
            organizacion=self.organizacion_propia,
            rol=Membresia.Rol.OPERADOR,
            estado=Membresia.Estado.ACTIVA,
        )

    def test_usuario_anonimo_recibe_401(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(
            respuesta.json()["error"],
            "Autenticación requerida.",
        )

    def test_usuario_solo_ve_su_organizacion_activa(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        ids = {
            item["id"]
            for item in respuesta.json()["resultados"]
        }

        self.assertIn(str(self.organizacion_propia.pk), ids)
        self.assertNotIn(str(self.organizacion_ajena.pk), ids)

    def test_no_aparecen_organizaciones_suspendidas(self):
        suspendida = Organizacion.objects.create(
            nombre="Organización suspendida API",
            tipo=Organizacion.Tipo.ONG,
            codigo="organizacion-suspendida-api",
            estado=Organizacion.Estado.SUSPENDIDA,
        )
        Membresia.objects.create(
            usuario=self.usuario,
            organizacion=suspendida,
            rol=Membresia.Rol.OPERADOR,
            estado=Membresia.Estado.ACTIVA,
        )

        self.client.force_login(self.usuario)
        respuesta = self.client.get(self.url)

        ids = {
            item["id"]
            for item in respuesta.json()["resultados"]
        }
        self.assertNotIn(str(suspendida.pk), ids)

    def test_superusuario_puede_consultar_todas_las_organizaciones(self):
        administrador = Usuario.objects.create_superuser(
            username="superusuario_api_org",
            email="superusuario-api-org@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )
        self.client.force_login(administrador)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        ids = {
            item["id"]
            for item in respuesta.json()["resultados"]
        }

        self.assertIn(str(self.organizacion_propia.pk), ids)
        self.assertIn(str(self.organizacion_ajena.pk), ids)

    def test_metodo_post_no_esta_permitido(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.post(self.url, data={})

        self.assertEqual(respuesta.status_code, 405)
