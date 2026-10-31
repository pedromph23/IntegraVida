#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/configuracion/admin.py << 'EOF'
from django.contrib import admin

from apps.configuracion.models import ReferenciaMigracion


@admin.register(ReferenciaMigracion)
class ReferenciaMigracionAdmin(admin.ModelAdmin):
    list_display = (
        "sistema_origen", "entidad_origen", "identificador_origen",
        "entidad_destino", "resultado_validacion", "creado_en",
    )
    list_filter = ("sistema_origen", "resultado_validacion")
    search_fields = ("entidad_origen", "identificador_origen", "entidad_destino")
    readonly_fields = (
        "id", "sistema_origen", "entidad_origen", "identificador_origen",
        "entidad_destino", "identificador_destino", "hash_origen",
        "resultado_validacion", "detalle_validacion", "migrado_por",
        "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
EOF

cat > apps/configuracion/tests.py << 'EOF'
"""Tests de Fase 10.1 — ReferenciaMigracion."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.configuracion.models import ReferenciaMigracion

Usuario = get_user_model()


class ReferenciaMigracionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Usuario.objects.create_user(
            username="mig-u", email="mig-u@test.local", password="x",
        )

    def _crear(self, sistema="COBIJO_VZLA", entidad="refugios", ident="REF-001"):
        return ReferenciaMigracion.objects.create(
            sistema_origen=sistema,
            entidad_origen=entidad,
            identificador_origen=ident,
            entidad_destino="refugios.Refugio",
            migrado_por=self.user,
        )

    def test_crear_valida(self):
        r = self._crear()
        self.assertEqual(
            r.resultado_validacion,
            ReferenciaMigracion.ResultadoValidacion.PENDIENTE,
        )
        self.assertEqual(
            r.sistema_origen,
            ReferenciaMigracion.SistemaOrigen.COBIJO_VZLA,
        )

    def test_unique_sistema_entidad_identificador(self):
        self._crear()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._crear()

    def test_mismo_ident_distinto_sistema_ok(self):
        self._crear(sistema="COBIJO_VZLA", entidad="refugios", ident="REF-1")
        r2 = self._crear(sistema="NUTRILINK", entidad="refugios", ident="REF-1")
        self.assertIsNotNone(r2.pk)

    def test_mismo_ident_distinta_entidad_ok(self):
        self._crear(entidad="refugios", ident="X-1")
        r2 = self._crear(entidad="insumos", ident="X-1")
        self.assertIsNotNone(r2.pk)

    def test_identificador_destino_nullable(self):
        r = self._crear()
        self.assertIsNone(r.identificador_destino)

    def test_resultado_pendiente_por_defecto(self):
        r = self._crear()
        self.assertEqual(r.resultado_validacion, "PENDIENTE")

    def test_actualizar_validacion(self):
        r = self._crear()
        r.resultado_validacion = (
            ReferenciaMigracion.ResultadoValidacion.VALIDADO
        )
        r.identificador_destino = "00000000-0000-0000-0000-000000000001"
        r.save()
        r.refresh_from_db()
        self.assertEqual(r.resultado_validacion, "VALIDADO")
        self.assertIsNotNone(r.identificador_destino)
EOF

echo "OK: admin + 7 tests"

echo ""
echo "▶ Verificación de imports (antes del check)"
python3 manage.py shell -c "from apps.configuracion import models, admin; print('OK: imports')"

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations configuracion
python3 manage.py migrate configuracion

echo ""
echo "▶ Tests configuracion"
python3 manage.py test apps.configuracion -v 2

echo ""
echo "▶ Regresión completa (11 apps)"
python3 manage.py test apps.reportes apps.inventario apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 10.1 COMPLETADA"
