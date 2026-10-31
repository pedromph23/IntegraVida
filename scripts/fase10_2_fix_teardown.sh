#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

# ── 1) Cerrar conexiones residuales a la DB de test ─────────────
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_integravida_db' AND pid <> pg_backend_pid();" || true
sudo -u postgres psql -c "DROP DATABASE IF EXISTS test_integravida_db;" || true

# ── 2) Aplicar el fix al archivo de tests ───────────────────────
python3 - << 'PY'
from pathlib import Path

p = Path("apps/configuracion/tests_integridad.py")
text = p.read_text(encoding="utf-8")

# Fix A: import connections al inicio
old_import = "from django.db import connection\n"
new_import = "from django.db import connection, connections\n"
if old_import in text and new_import not in text:
    text = text.replace(old_import, new_import, 1)
    print("OK: import connections")

# Fix B: cerrar connection en cada worker de ConcurrenciaStockTests
# Worker 1: _intentar_salida
old_w1 = '''    def _intentar_salida(self, cantidad):
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
'''
new_w1 = '''    def _intentar_salida(self, cantidad):
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
        finally:
            connection.close()
'''
if old_w1 in text:
    text = text.replace(old_w1, new_w1, 1)
    print("OK: fix worker _intentar_salida")

# Worker 2: entrada()
old_w2 = '''        def entrada():
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
'''
new_w2 = '''        def entrada():
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
            finally:
                connection.close()
'''
if old_w2 in text:
    text = text.replace(old_w2, new_w2, 1)
    print("OK: fix worker entrada")

# Worker 3: salida()
old_w3 = '''        def salida():
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
'''
new_w3 = '''        def salida():
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
            finally:
                connection.close()
'''
if old_w3 in text:
    text = text.replace(old_w3, new_w3, 1)
    print("OK: fix worker salida")

# Worker 4: _intentar_aceptar
old_w4 = '''    def _intentar_aceptar(self, derivacion_id):
        try:
            transicionar_derivacion(
                derivacion_id=derivacion_id,
                nuevo_estado=Derivacion.Estado.ACEPTADA,
                usuario=self.user,
            )
            return True
        except Exception:
            return False
'''
new_w4 = '''    def _intentar_aceptar(self, derivacion_id):
        try:
            transicionar_derivacion(
                derivacion_id=derivacion_id,
                nuevo_estado=Derivacion.Estado.ACEPTADA,
                usuario=self.user,
            )
            return True
        except Exception:
            return False
        finally:
            connection.close()
'''
if old_w4 in text:
    text = text.replace(old_w4, new_w4, 1)
    print("OK: fix worker _intentar_aceptar")

# Fix C: añadir tearDown a ConcurrenciaStockTests
old_td1 = '''class ConcurrenciaStockTests(TransactionTestCase):
    """Demuestra que dos movimientos simultáneos no dejan stock negativo."""

    def setUp(self):
        self.org = _org("conc1")
'''
new_td1 = '''class ConcurrenciaStockTests(TransactionTestCase):
    """Demuestra que dos movimientos simultáneos no dejan stock negativo."""

    def tearDown(self):
        connections.close_all()
        super().tearDown()

    def setUp(self):
        self.org = _org("conc1")
'''
if old_td1 in text and "def tearDown(self):\n        connections.close_all()" not in text[:4000]:
    text = text.replace(old_td1, new_td1, 1)
    print("OK: tearDown ConcurrenciaStockTests")

# Fix D: añadir tearDown a ConcurrenciaDerivacionTests
old_td2 = '''class ConcurrenciaDerivacionTests(TransactionTestCase):
    """Demuestra que dos transiciones simultáneas no duplican estado."""

    def setUp(self):
        self.org = _org("conc2")
'''
new_td2 = '''class ConcurrenciaDerivacionTests(TransactionTestCase):
    """Demuestra que dos transiciones simultáneas no duplican estado."""

    def tearDown(self):
        connections.close_all()
        super().tearDown()

    def setUp(self):
        self.org = _org("conc2")
'''
if old_td2 in text and "connections.close_all()" not in text[text.find(old_td2):text.find(old_td2) + 400]:
    text = text.replace(old_td2, new_td2, 1)
    print("OK: tearDown ConcurrenciaDerivacionTests")

p.write_text(text, encoding="utf-8")
PY

echo ""
echo "▶ Verificación de imports"
python3 manage.py shell -c "from apps.configuracion import tests_integridad; print('OK: imports')"
