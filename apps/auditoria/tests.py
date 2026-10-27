from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services import registrar_evento
from apps.usuarios.models import Usuario


class EventoAuditoriaModelTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="auditoria_prueba",
            email="auditoria@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )

    def test_registra_evento_exitoso(self):
        evento = EventoAuditoria.objects.create(
            actor=self.usuario,
            accion="ORGANIZACION_CONSULTADA",
            tipo_objeto="Organizacion",
            objeto_id="organizacion-prueba",
            resultado=EventoAuditoria.Resultado.EXITOSO,
            metadatos={"origen": "prueba automatizada"},
        )

        self.assertIsNotNone(evento.pk)
        self.assertEqual(evento.actor, self.usuario)
        self.assertEqual(
            evento.resultado,
            EventoAuditoria.Resultado.EXITOSO,
        )
        self.assertEqual(
            evento.metadatos["origen"],
            "prueba automatizada",
        )

    def test_registra_acceso_denegado(self):
        evento = EventoAuditoria.objects.create(
            actor=self.usuario,
            accion="ACCESO_DENEGADO",
            resultado=EventoAuditoria.Resultado.DENEGADO,
            justificacion="El usuario no tiene permiso.",
        )

        self.assertEqual(
            evento.resultado,
            EventoAuditoria.Resultado.DENEGADO,
        )
        self.assertTrue(evento.justificacion)

    def test_evento_se_conserva_si_se_elimina_el_usuario(self):
        evento = EventoAuditoria.objects.create(
            actor=self.usuario,
            accion="PRUEBA_CONSERVACION_HISTORICA",
        )
        evento_id = evento.pk

        self.usuario.delete()
        evento.refresh_from_db()

        self.assertEqual(evento.pk, evento_id)
        self.assertIsNone(evento.actor_id)
        self.assertEqual(
            evento.accion,
            "PRUEBA_CONSERVACION_HISTORICA",
        )


class RegistrarEventoServiceTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="servicio_auditoria",
            email="servicio@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )

    def test_registra_evento_con_metadatos_permitidos(self):
        organizacion_id = uuid4()

        evento = registrar_evento(
            accion="CONSULTA_PUBLICA",
            actor=self.usuario,
            organizacion_id=organizacion_id,
            tipo_objeto="Servicio",
            objeto_id="servicio-123",
            metadatos={"origen": "portal", "cantidad": 3},
        )

        self.assertEqual(evento.actor, self.usuario)
        self.assertEqual(evento.organizacion_id, organizacion_id)
        self.assertEqual(evento.metadatos["cantidad"], 3)

    def test_rechaza_claves_sensibles_incluso_anidadas(self):
        casos = [
            {"password": "no-debe-guardarse"},
            {"detalle": {"access_token": "secreto"}},
            {"elementos": [{"diagnostico": "dato clínico"}]},
        ]

        for metadatos in casos:
            with self.subTest(metadatos=metadatos):
                with self.assertRaises(ValidationError):
                    registrar_evento(
                        accion="PRUEBA_SEGURIDAD",
                        metadatos=metadatos,
                    )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_SEGURIDAD"
            ).exists()
        )

    def test_rechaza_identificador_de_organizacion_invalido(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_UUID",
                organizacion_id="no-es-un-uuid",
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_UUID"
            ).exists()
        )

    def test_rechaza_accion_vacia_o_demasiado_larga(self):
        for accion in ("", "A" * 101):
            with self.subTest(longitud=len(accion)):
                with self.assertRaises(ValidationError):
                    registrar_evento(accion=accion)

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="A" * 101
            ).exists()
        )


class RegistrarEventoValidacionTests(TestCase):
    def test_rechaza_resultado_invalido(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_RESULTADO",
                resultado="NO_EXISTE",
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_RESULTADO"
            ).exists()
        )

    def test_rechaza_clave_de_metadatos_no_autorizada(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_METADATOS",
                metadatos={"diagnostico": "informacion sensible"},
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_METADATOS"
            ).exists()
        )

    def test_rechaza_metadatos_anidados(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_ANIDADA",
                metadatos={"origen": {"detalle": "texto"}},
            )

    def test_rechaza_direccion_ip_invalida(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_IP",
                ip="999.999.999.999",
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_IP"
            ).exists()
        )

    def test_acepta_metadatos_tecnicos_autorizados(self):
        evento = registrar_evento(
            accion="PRUEBA_METADATOS_VALIDOS",
            metadatos={
                "origen": "portal",
                "cantidad": 3,
                "tipo_operacion": "consulta",
            },
        )

        self.assertEqual(evento.metadatos["origen"], "portal")
        self.assertEqual(evento.metadatos["cantidad"], 3)


class RegistrarEventoTiposInvalidosTests(TestCase):
    def test_rechaza_ip_que_no_es_texto(self):
        with self.assertRaises(ValidationError):
            registrar_evento(accion="PRUEBA_IP_TIPO", ip=["127.0.0.1"])

        self.assertFalse(
            EventoAuditoria.objects.filter(accion="PRUEBA_IP_TIPO").exists()
        )

    def test_rechaza_identificador_de_objeto_no_admitido(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_OBJETO_TIPO",
                objeto_id={"id": 1},
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_OBJETO_TIPO"
            ).exists()
        )

    def test_rechaza_correlacion_de_tipo_invalido(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_CORRELACION_TIPO",
                correlation_id=["no-valido"],
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_CORRELACION_TIPO"
            ).exists()
        )

    def test_rechaza_numero_no_finito_en_metadatos(self):
        with self.assertRaises(ValidationError):
            registrar_evento(
                accion="PRUEBA_NUMERO_NO_FINITO",
                metadatos={"cantidad": float("nan")},
            )

        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="PRUEBA_NUMERO_NO_FINITO"
            ).exists()
        )


class EventoAuditoriaAdminTests(TestCase):
    def setUp(self):
        from django.contrib import admin
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        self.usuario_admin = get_user_model().objects.create_superuser(
            username="admin_auditoria_prueba",
            email="admin-auditoria@example.test",
            password="ClaveTemporal-SoloPruebas-123!",
        )

        self.admin_model = admin.site._registry[EventoAuditoria]
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.usuario_admin

    def test_eventos_no_se_pueden_crear_desde_admin(self):
        self.assertFalse(
            self.admin_model.has_add_permission(self.request)
        )

    def test_eventos_no_se_pueden_editar_desde_admin(self):
        self.assertFalse(
            self.admin_model.has_change_permission(self.request)
        )

    def test_eventos_no_se_pueden_eliminar_desde_admin(self):
        self.assertFalse(
            self.admin_model.has_delete_permission(self.request)
        )

    def test_todos_los_campos_son_de_solo_lectura(self):
        campos_modelo = {
            campo.name for campo in EventoAuditoria._meta.fields
        }

        self.assertEqual(
            set(self.admin_model.readonly_fields),
            campos_modelo,
        )

    def test_superusuario_puede_consultar_listado_de_auditoria(self):
        self.client.force_login(self.usuario_admin)

        respuesta = self.client.get("/admin/auditoria/eventoauditoria/")

        self.assertEqual(respuesta.status_code, 200)
