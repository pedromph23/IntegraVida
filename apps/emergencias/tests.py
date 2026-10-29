import json
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.auditoria.models import EventoAuditoria
from apps.emergencias.models import Emergencia, ReporteEmergencia


class ConsultaPublicaEmergenciasTests(TestCase):
    """Pruebas de consulta pública de emergencias confirmadas."""

    @classmethod
    def setUpTestData(cls):
        cls.confirmada = Emergencia.objects.create(
            titulo="Inundación en zona residencial",
            descripcion="Anegamiento de varias calles.",
            categoria=Emergencia.Categoria.INUNDACION,
            gravedad=Emergencia.Gravedad.ALTA,
            estado=Emergencia.Estado.CONFIRMADA,
            ubicacion_texto="Sector Los Olivos",
        )

        cls.en_verificacion = Emergencia.objects.create(
            titulo="Reporte pendiente",
            descripcion="Situación aún sin verificar.",
            categoria=Emergencia.Categoria.OTRA,
            gravedad=Emergencia.Gravedad.MODERADA,
            estado=Emergencia.Estado.EN_VERIFICACION,
            ubicacion_texto="Ubicación pendiente",
        )

    def test_lista_publica_sin_autenticacion(self):
        respuesta = self.client.get(reverse("emergencias:lista"))

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()

        self.assertEqual(datos["total"], 1)
        self.assertEqual(
            datos["resultados"][0]["id"],
            str(self.confirmada.id),
        )

    def test_no_expone_emergencias_en_verificacion(self):
        respuesta = self.client.get(reverse("emergencias:lista"))

        self.assertEqual(respuesta.status_code, 200)
        ids = {
            item["id"]
            for item in respuesta.json()["resultados"]
        }

        self.assertIn(str(self.confirmada.id), ids)
        self.assertNotIn(str(self.en_verificacion.id), ids)

    def test_filtra_por_categoria(self):
        respuesta = self.client.get(
            reverse("emergencias:lista"),
            {"categoria": "INUNDACION"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 1)

    def test_rechaza_categoria_invalida(self):
        respuesta = self.client.get(
            reverse("emergencias:lista"),
            {"categoria": "INVENTADA"},
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_rechaza_limite_fuera_de_rango(self):
        respuesta = self.client.get(
            reverse("emergencias:lista"),
            {"limite": "500"},
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_detalle_publico(self):
        respuesta = self.client.get(
            reverse(
                "emergencias:detalle",
                kwargs={"emergencia_id": self.confirmada.id},
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json()["emergencia"]["id"],
            str(self.confirmada.id),
        )

    def test_detalle_no_disponible_para_emergencia_no_publica(self):
        respuesta = self.client.get(
            reverse(
                "emergencias:detalle",
                kwargs={"emergencia_id": self.en_verificacion.id},
            )
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_metodo_post_no_permitido(self):
        respuesta = self.client.post(
            reverse("emergencias:lista"),
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 405)


class RecepcionPublicaReportesTests(TestCase):
    """Pruebas de recepción anónima y validación de reportes."""

    def setUp(self):
        cache.clear()
        self.url = reverse("emergencias:crear-reporte")
        self.datos = {
            "descripcion": "Hay agua acumulada en varias viviendas.",
            "ubicacion_texto": "Sector Los Olivos",
            "referencia_lugar": "Cerca de la escuela",
            "categoria": Emergencia.Categoria.INUNDACION,
        }

    def enviar_reporte(self, datos=None):
        return self.client.post(
            self.url,
            data=json.dumps(self.datos if datos is None else datos),
            content_type="application/json",
        )

    def test_guarda_categoria_y_descripcion_por_separado(self):
        respuesta = self.enviar_reporte()

        self.assertEqual(respuesta.status_code, 201)
        reporte = ReporteEmergencia.objects.get(
            pk=respuesta.json()["reporte_id"]
        )

        self.assertEqual(
            reporte.categoria,
            Emergencia.Categoria.INUNDACION,
        )
        self.assertEqual(
            reporte.descripcion,
            self.datos["descripcion"],
        )

    def test_recibe_reporte_sin_autenticacion(self):
        respuesta = self.enviar_reporte()

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(
            respuesta.json()["estado_revision"],
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )
        self.assertEqual(ReporteEmergencia.objects.count(), 1)

    def test_registra_evento_de_auditoria(self):
        respuesta = self.enviar_reporte()

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(
            EventoAuditoria.objects.filter(
                accion="emergencia.reporte_publico",
                tipo_objeto="ReporteEmergencia",
                resultado=EventoAuditoria.Resultado.EXITOSO,
            ).exists()
        )

    def test_rechaza_json_invalido(self):
        respuesta = self.client.post(
            self.url,
            data="{json incorrecto",
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReporteEmergencia.objects.count(), 0)

    def test_rechaza_categoria_invalida(self):
        datos = {
            **self.datos,
            "categoria": "CATEGORIA_INVENTADA",
        }
        respuesta = self.enviar_reporte(datos)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReporteEmergencia.objects.count(), 0)

    def test_rechaza_descripcion_vacia(self):
        datos = {**self.datos, "descripcion": "   "}
        respuesta = self.enviar_reporte(datos)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReporteEmergencia.objects.count(), 0)

    def test_rechaza_campos_no_permitidos(self):
        datos = {
            **self.datos,
            "estado_revision": "VINCULADO",
        }
        respuesta = self.enviar_reporte(datos)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ReporteEmergencia.objects.count(), 0)

    def test_rechaza_tipo_de_contenido_incorrecto(self):
        respuesta = self.client.post(
            self.url,
            data="descripcion=Prueba",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(respuesta.status_code, 415)

    def test_no_acepta_get_para_enviar_reportes(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 405)

    def test_aplica_limite_de_reportes_por_ip(self):
        for _ in range(5):
            respuesta = self.enviar_reporte()
            self.assertEqual(respuesta.status_code, 201)

        respuesta = self.enviar_reporte()

        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(ReporteEmergencia.objects.count(), 5)


class AtomicidadReporteEmergenciaTests(TestCase):
    """La recepción del reporte y su auditoría deben ser atómicas."""

    def test_fallo_de_auditoria_revierte_el_reporte(self):
        url = reverse("emergencias:crear-reporte")
        datos = {
            "descripcion": "Inundación en varias viviendas.",
            "ubicacion_texto": "Sector de prueba",
            "referencia_lugar": "",
            "categoria": Emergencia.Categoria.INUNDACION,
        }

        with patch(
            "apps.emergencias.services.registrar_evento",
            side_effect=RuntimeError("Fallo simulado de auditoría"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    url,
                    data=json.dumps(datos),
                    content_type="application/json",
                )

        self.assertEqual(ReporteEmergencia.objects.count(), 0)
        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="emergencia.reporte_publico",
            ).exists()
        )


class RevisionInternaReportesTests(TestCase):
    """Permisos, revisión, vinculación y auditoría de reportes internos."""

    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        from apps.organizaciones.models import Organizacion, Membresia

        cls.operador = Usuario.objects.create_user(
            username="operador_revision",
            email="operador@example.test",
            password="Clave-Prueba-2026!",
        )
        cls.usuario_sin_permisos = Usuario.objects.create_user(
            username="usuario_sin_permisos",
            email="usuario@example.test",
            password="Clave-Prueba-2026!",
        )
        cls.superusuario = Usuario.objects.create_superuser(
            username="admin_revision",
            email="admin@example.test",
            password="Clave-Prueba-2026!",
        )

        cls.organizacion = Organizacion.objects.create(
            nombre="Organización de prueba",
            tipo=Organizacion.Tipo.ONG,
            codigo="organizacion-prueba-revision",
            estado=Organizacion.Estado.ACTIVA,
        )

        Membresia.objects.create(
            usuario=cls.operador,
            organizacion=cls.organizacion,
            rol=Membresia.Rol.OPERADOR,
            estado=Membresia.Estado.ACTIVA,
        )

        cls.emergencia = Emergencia.objects.create(
            titulo="Inundación de prueba",
            descripcion="Anegamiento reportado para pruebas.",
            categoria=Emergencia.Categoria.INUNDACION,
            gravedad=Emergencia.Gravedad.ALTA,
            estado=Emergencia.Estado.CONFIRMADA,
            ubicacion_texto="Sector de prueba",
        )

    def setUp(self):
        cache.clear()

        self.reporte = ReporteEmergencia.objects.create(
            categoria=Emergencia.Categoria.INUNDACION,
            descripcion="Agua acumulada en varias viviendas.",
            ubicacion_texto="Sector de prueba",
            canal=ReporteEmergencia.Canal.WEB,
            estado_revision=ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

        self.lista_url = reverse(
            "emergencias_internas:lista-reportes"
        )
        self.revision_url = reverse(
            "emergencias_internas:revisar-reporte",
            kwargs={"reporte_id": self.reporte.id},
        )
        self.vincular_url = reverse(
            "emergencias_internas:vincular-reporte",
            kwargs={"reporte_id": self.reporte.id},
        )

    def enviar_json(self, url, datos):
        return self.client.post(
            url,
            data=json.dumps(datos),
            content_type="application/json",
        )

    def test_usuario_anonimo_no_puede_consultar_cola(self):
        respuesta = self.client.get(self.lista_url)

        self.assertEqual(respuesta.status_code, 401)

    def test_usuario_sin_membresia_operativa_recibe_403(self):
        self.client.force_login(self.usuario_sin_permisos)

        respuesta = self.client.get(self.lista_url)

        self.assertEqual(respuesta.status_code, 403)

    def test_operador_activo_no_puede_consultar_cola_nacional(self):
        self.client.force_login(self.operador)

        respuesta = self.client.get(self.lista_url)

        self.assertEqual(respuesta.status_code, 403)

    def test_operador_no_puede_modificar_reportes_nacionales(self):
        self.client.force_login(self.operador)

        respuesta_revision = self.enviar_json(
            self.revision_url,
            {"estado_revision": "EN_REVISION"},
        )
        respuesta_vinculacion = self.enviar_json(
            self.vincular_url,
            {
                "emergencia_id": str(self.emergencia.id),
                "justificacion": "Prueba de restricción provisional.",
            },
        )

        self.assertEqual(respuesta_revision.status_code, 403)
        self.assertEqual(respuesta_vinculacion.status_code, 403)

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )
        self.assertIsNone(self.reporte.emergencia_id)

    def test_operador_puede_marcar_reporte_en_revision(self):
        self.client.force_login(self.superusuario)

        respuesta = self.enviar_json(
            self.revision_url,
            {"estado_revision": "EN_REVISION"},
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            f"Respuesta HTTP {respuesta.status_code}: "
            f"{respuesta.content.decode('utf-8', errors='replace')}",
        )

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.EN_REVISION,
        )
        self.assertTrue(
            EventoAuditoria.objects.filter(
                accion="emergencia.reporte_revision",
                objeto_id=str(self.reporte.id),
                actor=self.superusuario,
                resultado=EventoAuditoria.Resultado.EXITOSO,
            ).exists()
        )

    def test_descartar_reporte_exige_justificacion(self):
        self.client.force_login(self.superusuario)

        respuesta = self.enviar_json(
            self.revision_url,
            {"estado_revision": "DESCARTADO"},
        )

        self.assertEqual(respuesta.status_code, 400)

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

    def test_no_permite_marcar_vinculado_sin_emergencia(self):
        self.client.force_login(self.superusuario)

        respuesta = self.enviar_json(
            self.revision_url,
            {"estado_revision": "VINCULADO"},
        )

        self.assertEqual(respuesta.status_code, 400)

        self.reporte.refresh_from_db()
        self.assertIsNone(self.reporte.emergencia_id)

    def test_vincular_reporte_asocia_emergencia_y_audita(self):
        self.client.force_login(self.superusuario)

        respuesta = self.enviar_json(
            self.vincular_url,
            {
                "emergencia_id": str(self.emergencia.id),
                "justificacion": "Corresponde al mismo incidente.",
            },
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            f"Respuesta HTTP {respuesta.status_code}: "
            f"{respuesta.content.decode('utf-8', errors='replace')}",
        )

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.emergencia_id,
            self.emergencia.id,
        )
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.VINCULADO,
        )
        self.assertTrue(
            EventoAuditoria.objects.filter(
                accion="emergencia.reporte_vinculado",
                objeto_id=str(self.reporte.id),
                actor=self.superusuario,
            ).exists()
        )

    def test_fallo_de_auditoria_revierte_cambio_de_estado(self):
        self.client.force_login(self.superusuario)

        with patch(
            "apps.emergencias.servicios_revision.registrar_evento",
            side_effect=RuntimeError("Fallo de auditoría simulado"),
        ):
            with self.assertRaises(RuntimeError):
                self.enviar_json(
                    self.revision_url,
                    {"estado_revision": "EN_REVISION"},
                )

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

    def test_fallo_de_auditoria_revierte_vinculacion(self):
        self.client.force_login(self.superusuario)

        with patch(
            "apps.emergencias.servicios_revision.registrar_evento",
            side_effect=RuntimeError("Fallo de auditoría simulado"),
        ):
            with self.assertRaises(RuntimeError):
                self.enviar_json(
                    self.vincular_url,
                    {
                        "emergencia_id": str(self.emergencia.id),
                        "justificacion": "Prueba de atomicidad.",
                    },
                )

        self.reporte.refresh_from_db()
        self.assertIsNone(self.reporte.emergencia_id)
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )
        self.assertFalse(
            EventoAuditoria.objects.filter(
                accion="emergencia.reporte_vinculado",
                objeto_id=str(self.reporte.id),
            ).exists()
        )

    def test_servicios_rechazan_escrituras_sin_permisos(self):
        from django.core.exceptions import PermissionDenied
        from apps.emergencias.servicios_revision import (
            cambiar_estado_reporte,
            vincular_reporte_emergencia,
        )

        with self.assertRaises(PermissionDenied):
            cambiar_estado_reporte(
                reporte_id=self.reporte.id,
                estado_nuevo=ReporteEmergencia.EstadoRevision.EN_REVISION,
                justificacion="Prueba de autorización",
                usuario=self.usuario_sin_permisos,
                request=None,
            )

        with self.assertRaises(PermissionDenied):
            vincular_reporte_emergencia(
                reporte_id=self.reporte.id,
                emergencia_id=self.emergencia.id,
                justificacion="Prueba de autorización",
                usuario=self.usuario_sin_permisos,
                request=None,
            )

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )
        self.assertIsNone(self.reporte.emergencia_id)
        self.assertFalse(
            EventoAuditoria.objects.filter(
                objeto_id=str(self.reporte.id),
                accion__in=[
                    "emergencia.reporte_revision",
                    "emergencia.reporte_vinculado",
                ],
            ).exists()
        )

    def test_staff_sin_membresia_tampoco_puede_escribir_directamente(self):
        from django.core.exceptions import PermissionDenied
        from apps.emergencias.servicios_revision import (
            cambiar_estado_reporte,
            vincular_reporte_emergencia,
        )

        self.usuario_sin_permisos.is_staff = True
        self.usuario_sin_permisos.save(update_fields=["is_staff"])

        with self.assertRaises(PermissionDenied):
            cambiar_estado_reporte(
                reporte_id=self.reporte.id,
                estado_nuevo=ReporteEmergencia.EstadoRevision.EN_REVISION,
                justificacion="Prueba de usuario staff",
                usuario=self.usuario_sin_permisos,
                request=None,
            )

        with self.assertRaises(PermissionDenied):
            vincular_reporte_emergencia(
                reporte_id=self.reporte.id,
                emergencia_id=self.emergencia.id,
                justificacion="Prueba de usuario staff",
                usuario=self.usuario_sin_permisos,
                request=None,
            )

        self.reporte.refresh_from_db()
        self.assertEqual(
            self.reporte.estado_revision,
            ReporteEmergencia.EstadoRevision.PENDIENTE,
        )
        self.assertIsNone(self.reporte.emergencia_id)

    def test_staff_sin_superusuario_ni_membresia_no_tiene_acceso(self):
        self.usuario_sin_permisos.is_staff = True
        self.usuario_sin_permisos.save(update_fields=["is_staff"])
        self.client.force_login(self.usuario_sin_permisos)

        respuesta = self.client.get(self.lista_url)

        self.assertEqual(respuesta.status_code, 403)

class EmergenciasAdminProteccionTests(TestCase):
    """Los campos críticos no se editan directamente desde Django Admin."""

    @classmethod
    def setUpTestData(cls):
        cls.emergencia = Emergencia.objects.create(
            titulo="Emergencia para prueba administrativa",
            descripcion="Registro de prueba.",
            categoria=Emergencia.Categoria.INUNDACION,
            gravedad=Emergencia.Gravedad.ALTA,
            estado=Emergencia.Estado.CONFIRMADA,
            ubicacion_texto="Sector de prueba",
        )
        cls.reporte = ReporteEmergencia.objects.create(
            categoria=Emergencia.Categoria.INUNDACION,
            descripcion="Reporte para prueba administrativa.",
            ubicacion_texto="Sector de prueba",
            estado_revision=ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

    def setUp(self):
        self.request = RequestFactory().get("/admin/")
        self.request.user = get_user_model()(is_staff=True, is_superuser=True, is_active=True)

    def test_estado_de_emergencia_no_es_editable_en_admin(self):
        model_admin = admin.site._registry[Emergencia]
        formulario = model_admin.get_form(
            self.request,
            obj=self.emergencia,
        )

        self.assertNotIn("estado", formulario.base_fields)
        self.assertIn("estado", model_admin.get_readonly_fields(
            self.request, self.emergencia
        ))

    def test_estado_y_vinculo_de_reporte_no_son_editables_en_admin(self):
        model_admin = admin.site._registry[ReporteEmergencia]
        formulario = model_admin.get_form(
            self.request,
            obj=self.reporte,
        )

        self.assertNotIn("estado_revision", formulario.base_fields)
        self.assertNotIn("emergencia", formulario.base_fields)

        campos_solo_lectura = model_admin.get_readonly_fields(
            self.request, self.reporte
        )
        self.assertIn("estado_revision", campos_solo_lectura)
        self.assertIn("emergencia", campos_solo_lectura)
