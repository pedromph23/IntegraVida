from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.auditoria.models import (
    HASH_GENESIS,
    EventoAuditoria,
    NotAllowed,
    calcular_hash,
)
from apps.auditoria.services import registrar_evento

Usuario = get_user_model()


class HashEncadenadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = Usuario.objects.create_user(username="auditor_test", password="x")

    def test_primer_evento_usa_genesis(self):
        evento = registrar_evento(actor=self.actor, accion="test.genesis")
        self.assertEqual(evento.hash_anterior, HASH_GENESIS)
        self.assertEqual(len(evento.hash_actual), 64)

    def test_cadena_secuencial(self):
        e1 = registrar_evento(actor=self.actor, accion="test.a")
        e2 = registrar_evento(actor=self.actor, accion="test.b")
        e3 = registrar_evento(actor=self.actor, accion="test.c")
        self.assertEqual(e2.hash_anterior, e1.hash_actual)
        self.assertEqual(e3.hash_anterior, e2.hash_actual)

    def test_hash_determinista(self):
        evento = registrar_evento(actor=self.actor, accion="test.det")
        self.assertEqual(calcular_hash(evento), evento.hash_actual)


class InmutabilidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = Usuario.objects.create_user(username="auditor_inmutable", password="x")

    def test_no_update_instance(self):
        evento = registrar_evento(actor=self.actor, accion="test.no_update")
        evento.accion = "intento_modificacion"
        with self.assertRaises(NotAllowed):
            evento.save()

    def test_no_delete_instance(self):
        evento = registrar_evento(actor=self.actor, accion="test.no_delete")
        with self.assertRaises(NotAllowed):
            evento.delete()

    def test_no_manager_update(self):
        registrar_evento(actor=self.actor, accion="test.mgr_update")
        with self.assertRaises(NotAllowed):
            EventoAuditoria.objects.update(accion="intento")

    def test_no_manager_delete(self):
        registrar_evento(actor=self.actor, accion="test.mgr_delete")
        with self.assertRaises(NotAllowed):
            EventoAuditoria.objects.all().delete()