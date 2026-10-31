from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.auditoria.models import EventoAuditoria
from apps.hospitales.models import (
    Hospital,
    HospitalServicio,
    RecursoHospitalario,
    RegistroDisponibilidad,
    Servicio,
)
from apps.hospitales.services import registrar_disponibilidad
from apps.organizaciones.models import Organizacion

Usuario = get_user_model()


def _org(slug="h-org"):
    return Organizacion.objects.create(
        nombre=f"Org {slug}",
        tipo=Organizacion.Tipo.HOSPITAL,
        codigo=slug,
        estado=Organizacion.Estado.ACTIVA,
    )


def _hospital(org, slug="h-1"):
    return Hospital.objects.create(
        codigo=slug,
        nombre=f"Hospital {slug}",
        tipo=Hospital.Tipo.HOSPITAL,
        nivel=Hospital.Nivel.NIVEL_III,
        organizacion=org,
        direccion="Calle x",
        estado_operativo=Hospital.EstadoOperativo.DISPONIBLE,
    )


class HospitalModeloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-m")

    def test_crear_hospital_valido(self):
        h = _hospital(self.org, "h-valid")
        self.assertEqual(h.tipo, Hospital.Tipo.HOSPITAL)
        self.assertEqual(h.nivel, Hospital.Nivel.NIVEL_III)
        self.assertEqual(h.estado_operativo, Hospital.EstadoOperativo.DISPONIBLE)

    def test_codigo_unico(self):
        _hospital(self.org, "h-dup")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _hospital(self.org, "h-dup")

    def test_servicios_m2m_through(self):
        h = _hospital(self.org, "h-svc")
        s, _ = Servicio.objects.get_or_create(
            codigo="test-svc-m2m",
            defaults={
                "nombre": "Servicio Test M2M",
                "tipo": Servicio.Tipo.SERVICIO,
            },
        )
        HospitalServicio.objects.create(hospital=h, servicio=s, disponible=True)
        self.assertEqual(h.servicios.count(), 1)
        self.assertTrue(h.servicios_through.first().disponible)

    def test_unique_hospital_servicio(self):
        h = _hospital(self.org, "h-svc2")
        s, _ = Servicio.objects.get_or_create(
            codigo="test-svc-uniq",
            defaults={
                "nombre": "Servicio Test Uniq",
                "tipo": Servicio.Tipo.ESPECIALIDAD,
            },
        )
        HospitalServicio.objects.create(hospital=h, servicio=s)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HospitalServicio.objects.create(hospital=h, servicio=s)


class RecursoHospitalarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-r")
        cls.hospital = _hospital(cls.org, "h-rec")

    def test_unique_hospital_tipo(self):
        RecursoHospitalario.objects.create(
            hospital=self.hospital,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=5,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RecursoHospitalario.objects.create(
                    hospital=self.hospital,
                    tipo=RecursoHospitalario.Tipo.UCI,
                    capacidad_total=5,
                    disponible=2,
                )

    def test_check_disponible_le_capacidad_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RecursoHospitalario.objects.create(
                    hospital=self.hospital,
                    tipo=RecursoHospitalario.Tipo.URGENCIA,
                    capacidad_total=5,
                    disponible=10,
                )

    def test_ocupados_property(self):
        r = RecursoHospitalario.objects.create(
            hospital=self.hospital,
            tipo=RecursoHospitalario.Tipo.QUIROFANO,
            capacidad_total=4,
            disponible=1,
        )
        self.assertEqual(r.ocupados, 3)


class RegistrarDisponibilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = _org("h-d")
        cls.usuario = Usuario.objects.create_user(username="h-u", password="x")
        cls.hospital = _hospital(cls.org, "h-disp")
        cls.recurso = RecursoHospitalario.objects.create(
            hospital=cls.hospital,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=3,
        )

    def test_actualiza_disponibilidad(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
        )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.disponible, 7)

    def test_crea_registro_historial(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
            notas="Ingreso de 4 pacientes",
        )
        self.assertEqual(RegistroDisponibilidad.objects.count(), 1)
        r = RegistroDisponibilidad.objects.first()
        self.assertEqual(r.cantidad_anterior, 3)
        self.assertEqual(r.cantidad_nueva, 7)
        self.assertEqual(r.diferencia, 4)

    def test_audita_cambio(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=7,
            usuario=self.usuario,
        )
        self.assertEqual(
            EventoAuditoria.objects.filter(
                accion="hospital.disponibilidad_actualizada"
            ).count(),
            1,
        )

    def test_rechaza_exceso_capacidad(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id=self.recurso.id,
                cantidad_nueva=20,
                usuario=self.usuario,
            )
        self.recurso.refresh_from_db()
        self.assertEqual(self.recurso.disponible, 3)

    def test_rechaza_negativa(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id=self.recurso.id,
                cantidad_nueva=-1,
                usuario=self.usuario,
            )

    def test_idempotente_si_igual(self):
        registrar_disponibilidad(
            recurso_id=self.recurso.id,
            cantidad_nueva=3,
            usuario=self.usuario,
        )
        self.assertEqual(RegistroDisponibilidad.objects.count(), 0)

    def test_recurso_inexistente(self):
        with self.assertRaises(ValidationError):
            registrar_disponibilidad(
                recurso_id="00000000-0000-0000-0000-000000000000",
                cantidad_nueva=1,
                usuario=self.usuario,
            )


# ══════════════════════════════════════════════════════════════════
# Portal público de hospitales (Fase 6.1.5)
# ══════════════════════════════════════════════════════════════════

from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from apps.hospitales.models import Servicio as ServicioModel


class PortalPublicoHospitalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organizacion.objects.create(
            nombre="Org Portal",
            tipo=Organizacion.Tipo.HOSPITAL,
            codigo="org-portal",
            estado=Organizacion.Estado.ACTIVA,
        )
        cls.disponible = Hospital.objects.create(
            codigo="pub-disp",
            nombre="Hospital Disponible",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III,
            organizacion=cls.org,
            direccion="Calle 1",
            estado_operativo=Hospital.EstadoOperativo.DISPONIBLE,
        )
        cls.saturado = Hospital.objects.create(
            codigo="pub-sat",
            nombre="Hospital Saturado",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_II,
            organizacion=cls.org,
            direccion="Calle 2",
            estado_operativo=Hospital.EstadoOperativo.SATURADO,
        )
        cls.colapsado = Hospital.objects.create(
            codigo="pub-col",
            nombre="Hospital Colapsado",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_IV,
            organizacion=cls.org,
            direccion="Calle 3",
            estado_operativo=Hospital.EstadoOperativo.COLAPSADO,
        )
        cls.no_op = Hospital.objects.create(
            codigo="pub-no",
            nombre="Hospital No Operativo",
            tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_I,
            organizacion=cls.org,
            direccion="Calle 4",
            estado_operativo=Hospital.EstadoOperativo.NO_OPERATIVO,
        )

    def test_lista_anonima_200(self):
        r = self.client.get(reverse("hospitales:lista"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("resultados", r.json())

    def test_solo_estados_publicos(self):
        r = self.client.get(reverse("hospitales:lista"))
        codigos = {h["codigo"] for h in r.json()["resultados"]}
        self.assertIn("pub-disp", codigos)
        self.assertIn("pub-sat", codigos)
        self.assertNotIn("pub-col", codigos)
        self.assertNotIn("pub-no", codigos)

    def test_no_expone_campos_prohibidos(self):
        r = self.client.get(reverse("hospitales:lista"))
        primer = r.json()["resultados"][0]
        for campo in (
            "organizacion", "organizacion_id",
            "responsable", "responsable_id",
            "notas_internas",
        ):
            self.assertNotIn(campo, primer)

    def test_estructura_recursos_todos_los_tipos(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        recursos = r.json()["hospital"]["recursos"]
        for tipo in ("uci", "urgencia", "quirofano", "hospitalizacion"):
            self.assertIn(tipo, recursos)
            self.assertIn("estado", recursos[tipo])
            self.assertIn(
                recursos[tipo]["estado"],
                ("disponible", "no_disponible", "sin_datos"),
            )

    def test_sin_recurso_reporta_sin_datos(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.json()["hospital"]["recursos"]["uci"]["estado"], "sin_datos")

    def test_recurso_fresco_disponible(self):
        RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.UCI,
            capacidad_total=10,
            disponible=3,
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.json()["hospital"]["recursos"]["uci"]["estado"], "disponible")

    def test_recurso_sin_disponibilidad(self):
        RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.URGENCIA,
            capacidad_total=20,
            disponible=0,
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(
            r.json()["hospital"]["recursos"]["urgencia"]["estado"],
            "no_disponible",
        )

    def test_recurso_desactualizado_sin_datos(self):
        r = RecursoHospitalario.objects.create(
            hospital=self.disponible,
            tipo=RecursoHospitalario.Tipo.QUIROFANO,
            capacidad_total=5,
            disponible=2,
        )
        RecursoHospitalario.objects.filter(pk=r.pk).update(
            actualizado_en=timezone.now() - timedelta(hours=3)
        )
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(
            r.json()["hospital"]["recursos"]["quirofano"]["estado"],
            "sin_datos",
        )

    def test_filtro_tipo_invalido_400(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"tipo": "INVALIDO"}
        )
        self.assertEqual(r.status_code, 400)

    def test_filtro_nivel(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"nivel": "NIVEL_III"}
        )
        self.assertEqual(r.status_code, 200)

    def test_filtro_estado_invalido_400(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"estado_operativo": "COLAPSADO"}
        )
        self.assertEqual(r.status_code, 400)

    def test_filtro_servicio(self):
        svc = ServicioModel.objects.create(
            codigo="test-svc-xyz",
            nombre="Servicio Test",
            tipo=ServicioModel.Tipo.SERVICIO,
        )
        HospitalServicio.objects.create(
            hospital=self.disponible, servicio=svc, disponible=True
        )
        r = self.client.get(
            reverse("hospitales:lista"), {"servicio": "test-svc-xyz"}
        )
        codigos = {h["codigo"] for h in r.json()["resultados"]}
        self.assertIn("pub-disp", codigos)
        self.assertNotIn("pub-sat", codigos)

    def test_detalle_activo_200(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-disp"])
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["hospital"]["codigo"], "pub-disp")

    def test_detalle_colapsado_404(self):
        r = self.client.get(
            reverse("hospitales:detalle", args=["pub-col"])
        )
        self.assertEqual(r.status_code, 404)

    def test_detalle_inexistente_404_identico_a_oculto(self):
        a = self.client.get(
            reverse("hospitales:detalle", args=["no-existe-xyz"])
        )
        b = self.client.get(
            reverse("hospitales:detalle", args=["pub-col"])
        )
        self.assertEqual(a.status_code, 404)
        self.assertEqual(b.status_code, 404)
        self.assertEqual(a.json(), b.json())

    def test_paginacion_offset(self):
        r = self.client.get(
            reverse("hospitales:lista"), {"limite": 1, "offset": 1}
        )
        data = r.json()
        self.assertEqual(data["limite"], 1)
        self.assertEqual(data["offset"], 1)
        self.assertEqual(len(data["resultados"]), 1)


class CatalogoServiciosPrecargadosTests(TestCase):
    def test_servicios_comunes_existen(self):
        esperados = [
            "emergencia", "uci", "pediatria", "cardiologia",
            "cirugia_general", "quirofano", "hospitalizacion",
        ]
        for codigo in esperados:
            self.assertTrue(
                ServicioModel.objects.filter(codigo=codigo).exists(),
                f"Falta el servicio precargado: {codigo}",
            )
