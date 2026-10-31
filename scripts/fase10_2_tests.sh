#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/configuracion/tests_integridad.py << 'EOF'
"""Tests de Fase 10.2 — concurrencia e integridad (§18.2, §18.3)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.derivaciones.models import Derivacion
from apps.derivaciones.services import (
    solicitar_derivacion, transicionar_derivacion,
)
from apps.hospitales.models import Hospital
from apps.inventario.models import (
    Almacen, Insumo, Lote, Movimiento, Stock,
)
from apps.inventario.services import registrar_movimiento
from apps.organizaciones.models import Membresia, Organizacion
from apps.pacientes.models import Episodio
from apps.pacientes.services import (
    crear_paciente, filtrar_episodios_por_ambito,
)
from apps.refugios.models import Refugio
from apps.territorio.models import EntidadFederal, Municipio

Usuario = get_user_model()


def _org(slug):
    return Organizacion.objects.create(
        nombre=f"Org {slug}", tipo=Organizacion.Tipo.ONG,
        codigo=f"org-{slug}", estado=Organizacion.Estado.ACTIVA,
    )


def _usuario(slug, rol=Membresia.Rol.COORDINADOR):
    u = Usuario.objects.create_user(
        username=f"u-{slug}", email=f"u-{slug}@test.local", password="x",
    )
    return u


def _membresia(user, org, rol=Membresia.Rol.COORDINADOR, municipio=None):
    return Membresia.objects.create(
        usuario=user, organizacion=org, rol=rol,
        estado=Membresia.Estado.ACTIVA, ambito_municipio=municipio,
    )


def _crear_stock_con_cantidad(almacen, lote, cantidad):
    return Stock.objects.create(
        almacen=almacen, lote=lote, cantidad=Decimal(str(cantidad)),
    )


# ══════════════════════════════════════════════════════════════════
# CONCURRENCIA — usa TransactionTestCase
# ══════════════════════════════════════════════════════════════════

class ConcurrenciaStockTests(TransactionTestCase):
    """Demuestra que dos movimientos simultáneos no dejan stock negativo."""

    def setUp(self):
        self.org = _org("conc1")
        self.hospital = Hospital.objects.create(
            codigo="h-conc1", nombre="H", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=self.org,
            direccion="x",
        )
        self.almacen = Almacen.objects.create(
            codigo="alm-conc1", nombre="A", organizacion=self.org,
            hospital=self.hospital,
        )
        self.user = _usuario("conc1")
        _membresia(self.user, self.org)
        self.insumo = Insumo.objects.create(
            codigo="ins-conc1", nombre="Med",
            categoria=Insumo.Categoria.MEDICINA,
            unidad_medida=Insumo.UnidadMedida.UNIDAD,
            requiere_lote=True,
        )
        self.lote = Lote.objects.create(insumo=self.insumo, codigo="L-C1")
        self.stock = _crear_stock_con_cantidad(self.almacen, self.lote, "10")

    def _intentar_salida(self, cantidad):
        """Ejecuta registrar_movimiento en este hilo. Retorna True si OK."""
        try:
            registrar_movimiento(
                stock_id=self.stock.pk,
                tipo=Movimiento.Tipo.SALIDA,
                cantidad=cantidad,
                usuario=self.user,
            )
            return True
        except (ValidationError, Exception):
            return False

    def test_dos_salidas_simultaneas_no_dejan_stock_negativo(self):
        """
        Stock inicial = 10. Dos hilos piden SALIDA 8 cada uno.

        Solo uno puede tener éxito: 10-8=2 >= 0.
        El otro debe fallar: 2-8=-6 < 0.
        Stock final debe ser 2 (nunca negativo).
        """
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [
                ex.submit(self._intentar_salida, 8)
                for _ in range(2)
            ]
            resultados = [f.result() for f in futures]

        self.assertEqual(
            sum(resultados), 1,
            f"Esperaba exactamente 1 éxito, obtuve {resultados}",
        )

        # Cerrar la conexión del hilo actual para leer el estado real
        connection.close()
        self.stock.refresh_from_db()
        self.assertGreaterEqual(self.stock.cantidad, Decimal("0"))
        self.assertEqual(self.stock.cantidad, Decimal("2.000"))

        # Debe haber 1 movimiento exitoso
        self.assertEqual(
            Movimiento.objects.filter(stock=self.stock).count(), 1,
        )

    def test_entrada_y_salida_simultaneas_conservan_consistencia(self):
        """
        Stock=10. Un hilo suma 5 (ENTRADA), otro resta 3 (SALIDA).

        Ambos deben completarse sin error. Stock final = 10+5-3 = 12.
        El orden exacto no importa, ambos son válidos por separado.
        """
        def entrada():
            try:
                registrar_movimiento(
                    stock_id=self.stock.pk,
                    tipo=Movimiento.Tipo.ENTRADA,
                    cantidad=5,
                    usuario=self.user,
                )
                return True
            except Exception:
                return False

        def salida():
            try:
                registrar_movimiento(
                    stock_id=self.stock.pk,
                    tipo=Movimiento.Tipo.SALIDA,
                    cantidad=3,
                    usuario=self.user,
                )
                return True
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(entrada), ex.submit(salida)]
            resultados = [f.result() for f in futures]

        self.assertEqual(sum(resultados), 2, f"Ambos deben pasar: {resultados}")

        connection.close()
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad, Decimal("12.000"))
        self.assertEqual(
            Movimiento.objects.filter(stock=self.stock).count(), 2,
        )


class ConcurrenciaDerivacionTests(TransactionTestCase):
    """Demuestra que dos transiciones simultáneas no duplican estado."""

    def setUp(self):
        self.org = _org("conc2")
        self.hospital_origen = Hospital.objects.create(
            codigo="h-o-c2", nombre="H Origen", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=self.org,
            direccion="x",
        )
        self.hospital_destino = Hospital.objects.create(
            codigo="h-d-c2", nombre="H Destino", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=self.org,
            direccion="y",
        )
        self.user = _usuario("conc2")
        _membresia(self.user, self.org)
        self.paciente = crear_paciente(
            nombres="Paciente", apellidos="Conc", usuario=self.user,
        )
        self.episodio = Episodio.objects.create(
            paciente=self.paciente, hospital=self.hospital_origen,
            motivo_consulta="Test", registrado_por=self.user,
        )

    def _intentar_aceptar(self, derivacion_id):
        try:
            transicionar_derivacion(
                derivacion_id=derivacion_id,
                nuevo_estado=Derivacion.Estado.ACEPTADA,
                usuario=self.user,
            )
            return True
        except Exception:
            return False

    def test_dos_aceptaciones_simultaneas_solo_una_pasa(self):
        derivacion = solicitar_derivacion(
            episodio_id=self.episodio.pk,
            hospital_destino=self.hospital_destino,
            motivo="Test",
            usuario=self.user,
        )

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [
                ex.submit(self._intentar_aceptar, derivacion.pk)
                for _ in range(2)
            ]
            resultados = [f.result() for f in futures]

        self.assertEqual(
            sum(resultados), 1,
            f"Solo una aceptación debe pasar: {resultados}",
        )

        connection.close()
        derivacion.refresh_from_db()
        self.assertEqual(derivacion.estado, Derivacion.Estado.ACEPTADA)


# ══════════════════════════════════════════════════════════════════
# PERMISOS CRUZADOS — usa TestCase normal
# ══════════════════════════════════════════════════════════════════

class AislamientoOrganizacionesTests(TestCase):
    """§18.2: usuario de org A no accede a datos de org B."""

    @classmethod
    def setUpTestData(cls):
        cls.org_a = _org("aisl-a")
        cls.org_b = _org("aisl-b")

        cls.user_a = _usuario("aisl-a")
        _membresia(cls.user_a, cls.org_a)

        cls.user_b = _usuario("aisl-b")
        _membresia(cls.user_b, cls.org_b)

        cls.hosp_a = Hospital.objects.create(
            codigo="h-aisl-a", nombre="HA", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org_a,
            direccion="x",
        )
        cls.hosp_b = Hospital.objects.create(
            codigo="h-aisl-b", nombre="HB", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org_b,
            direccion="y",
        )

        cls.pac_a = crear_paciente(
            nombres="PacienteA", apellidos="Apell", usuario=cls.user_a,
        )
        cls.pac_b = crear_paciente(
            nombres="PacienteB", apellidos="Apell", usuario=cls.user_b,
        )

        cls.ep_a = Episodio.objects.create(
            paciente=cls.pac_a, hospital=cls.hosp_a,
            motivo_consulta="A", registrado_por=cls.user_a,
        )
        cls.ep_b = Episodio.objects.create(
            paciente=cls.pac_b, hospital=cls.hosp_b,
            motivo_consulta="B", registrado_por=cls.user_b,
        )

    def test_usuario_a_no_ve_episodios_de_org_b(self):
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.user_a,
        )
        self.assertIn(self.ep_a, qs)
        self.assertNotIn(self.ep_b, qs)

    def test_usuario_b_no_ve_episodios_de_org_a(self):
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.user_b,
        )
        self.assertIn(self.ep_b, qs)
        self.assertNotIn(self.ep_a, qs)

    def test_superusuario_ve_todo(self):
        superuser = Usuario.objects.create_user(
            username="super", email="super@test.local",
            password="x", is_superuser=True,
        )
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), superuser,
        )
        self.assertIn(self.ep_a, qs)
        self.assertIn(self.ep_b, qs)

    def test_usuario_sin_membresia_no_ve_nada(self):
        sin_mem = _usuario("sin-mem")
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), sin_mem,
        )
        self.assertEqual(qs.count(), 0)

    def test_usuario_de_org_a_no_puede_solicitar_derivacion_de_org_b(self):
        with self.assertRaises(PermissionDenied):
            solicitar_derivacion(
                episodio_id=self.ep_b.pk,
                hospital_destino=self.hosp_a,
                motivo="Intento cruzado",
                usuario=self.user_a,
            )


class AmbitoTerritorialTests(TestCase):
    """§8: usuario con ámbito restringido no ve fuera de su municipio."""

    @classmethod
    def setUpTestData(cls):
        cls.org = _org("amb-terr")

        cls.entidad = EntidadFederal.objects.create(
            nombre="Distrito Capital", codigo="DC",
            tipo=EntidadFederal.Tipo.ESTADO,
        )
        cls.municipio_a = Municipio.objects.create(
            entidad_federal=cls.entidad, nombre="Libertador",
            codigo="DC-LIB",
        )
        cls.municipio_b = Municipio.objects.create(
            entidad_federal=cls.entidad, nombre="Chacao",
            codigo="DC-CHA",
        )

        cls.hosp_a = Hospital.objects.create(
            codigo="h-amb-a", nombre="HA", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org,
            direccion="x", municipio=cls.municipio_a,
        )
        cls.hosp_b = Hospital.objects.create(
            codigo="h-amb-b", nombre="HB", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org,
            direccion="y", municipio=cls.municipio_b,
        )

        cls.user_restringido = _usuario("amb-restr")
        _membresia(
            cls.user_restrigido if hasattr(cls, "user_restrigido") else cls.user_restringido,
            cls.org, municipio=cls.municipio_a,
        )

        cls.user_global = _usuario("amb-glob")
        _membresia(cls.user_global, cls.org)

        cls.pac = crear_paciente(
            nombres="Pac", apellidos="Amb", usuario=cls.user_global,
        )
        cls.ep_a = Episodio.objects.create(
            paciente=cls.pac, hospital=cls.hosp_a,
            motivo_consulta="A", registrado_por=cls.user_global,
        )
        cls.ep_b = Episodio.objects.create(
            paciente=cls.pac, hospital=cls.hosp_b,
            motivo_consulta="B", registrado_por=cls.user_global,
        )

    def test_usuario_restringido_solo_ve_su_municipio(self):
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.user_restringido,
        )
        self.assertIn(self.ep_a, qs)
        self.assertNotIn(self.ep_b, qs)

    def test_usuario_sin_restriccion_ve_todos(self):
        qs = filtrar_episodios_por_ambito(
            Episodio.objects.all(), self.user_global,
        )
        self.assertIn(self.ep_a, qs)
        self.assertIn(self.ep_b, qs)


class SuperuserNoTieneAccesoClinicoAutomaticoTests(TestCase):
    """§7.5: ser superusuario no implica leer expedientes automáticamente."""

    @classmethod
    def setUpTestData(cls):
        cls.org = _org("super-cli")
        cls.user_normal = _usuario("super-normal")
        _membresia(cls.user_normal, cls.org)
        cls.superuser = Usuario.objects.create_user(
            username="super-cli-user", email="super-cli@test.local",
            password="x", is_superuser=True,
        )

        cls.hosp = Hospital.objects.create(
            codigo="h-super", nombre="H", tipo=Hospital.Tipo.HOSPITAL,
            nivel=Hospital.Nivel.NIVEL_III, organizacion=cls.org,
            direccion="x",
        )

        cls.pac = crear_paciente(
            nombres="Pac", apellidos="Super", usuario=cls.user_normal,
        )
        cls.ep = Episodio.objects.create(
            paciente=cls.pac, hospital=cls.hosp,
            motivo_consulta="x", registrado_por=cls.user_normal,
        )

    def test_superuser_sin_membresia_no_accede_por_ambito(self):
        """
        Un superusuario SIN membresía en la organización del hospital
        NO accede a través de `tiene_acceso_a_organizacion`.
        La administración de plataforma es separada (§8).
        """
        from apps.organizaciones.services import tiene_acceso_a_organizacion
        self.assertFalse(
            tiene_acceso_a_organizacion(self.superuser, self.org)
        )

    def test_superuser_admin_plataforma_ve_todo(self):
        """
        Pero `puede_administrar_plataforma` sí le concede acceso global
        para reportes agregados (no para expedientes individuales).
        """
        from apps.organizaciones.services import puede_administrar_plataforma
        self.assertTrue(puede_administrar_plataforma(self.superuser))
EOF

echo "OK: tests_integridad.py creado"

echo ""
echo "▶ Verificación de imports"
python3 manage.py shell -c "from apps.configuracion import tests_integridad; print('OK: imports')"

echo ""
echo "▶ Tests integridad (concurrencia + permisos)"
python3 manage.py test apps.configuracion.tests_integridad -v 2

echo ""
echo "▶ Regresión completa"
python3 manage.py test apps.configuracion apps.reportes apps.inventario apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 10.2 COMPLETADA"
