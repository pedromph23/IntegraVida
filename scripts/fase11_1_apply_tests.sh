#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Verificar que no hay queries rotas por cedula en plaintext"
BAD=$(grep -rn "Paciente.objects.filter(cedula=" apps/ 2>/dev/null \
      | grep -v "cedula_hash" || true)
if [ -n "$BAD" ]; then
    echo "⚠ ADVERTENCIA: queries por 'cedula' (plaintext) detectadas:"
    echo "$BAD"
    echo "  Estas queries NO funcionarán después del cifrado."
    echo "  Deben usar 'cedula_hash'."
else
    echo "OK: no hay queries por cedula en plaintext"
fi

echo ""
echo "▶ 2. Aplicar migración 0002"
python3 manage.py migrate pacientes

echo ""
echo "▶ 3. Añadir tests de cifrado"
cat >> apps/pacientes/tests.py << 'PYEOF'


# ══════════════════════════════════════════════════════════════════
# Cifrado de campos clínicos (Fase 11.1)
# ══════════════════════════════════════════════════════════════════

from django.db import connection


class CifradoCamposPacienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username="cif-u", email="cif-u@test.local", password="x",
        )

    def test_roundtrip_cifrado(self):
        p = crear_paciente(
            cedula="V-12345678",
            nombres="Ana María",
            apellidos="Pérez González",
            telefono="0414-1234567",
            email="ana@test.local",
            notas_internas="Paciente con alergia a penicilina",
            usuario=self.usuario,
        )
        p_fresco = Paciente.objects.get(pk=p.pk)
        self.assertEqual(p_fresco.cedula, "V-12345678")
        self.assertEqual(p_fresco.nombres, "Ana María")
        self.assertEqual(p_fresco.apellidos, "Pérez González")
        self.assertEqual(p_fresco.telefono, "0414-1234567")
        self.assertEqual(p_fresco.email, "ana@test.local")
        self.assertEqual(
            p_fresco.notas_internas,
            "Paciente con alergia a penicilina",
        )

    def test_datos_cifrados_en_bd(self):
        p = crear_paciente(
            cedula="V-87654321",
            nombres="Carlos",
            apellidos="Rodríguez",
            usuario=self.usuario,
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT cedula, nombres, apellidos "
                "FROM pacientes_paciente WHERE id = %s",
                [str(p.pk)],
            )
            row = cur.fetchone()

        cedula_raw, nombres_raw, apellidos_raw = row

        # Los valores crudos en la BD NO deben ser el plaintext
        self.assertNotEqual(cedula_raw, "V-87654321")
        self.assertNotEqual(nombres_raw, "Carlos")
        self.assertNotEqual(apellidos_raw, "Rodríguez")

        # Y deben ser strings base64 (Fernet token empieza con "gAAAAA")
        self.assertTrue(cedula_raw.startswith("gAAAAA"))
        self.assertTrue(nombres_raw.startswith("gAAAAA"))
        self.assertTrue(apellidos_raw.startswith("gAAAAA"))

    def test_cedula_hash_sigue_funcionando(self):
        p = crear_paciente(
            cedula="V-11111111",
            nombres="Test",
            apellidos="Hash",
            usuario=self.usuario,
        )
        encontrado = buscar_paciente_por_cedula("V-11111111")
        self.assertEqual(encontrado, p)
        # El hash se calculó sobre el plaintext, no sobre el ciphertext
        self.assertEqual(encontrado.cedula, "V-11111111")

    def test_datos_legacy_se_toleran(self):
        # Simular una fila con datos legacy en plaintext (pre-migración)
        p = crear_paciente(
            nombres="Legacy",
            apellidos="Test",
            usuario=self.usuario,
        )
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE pacientes_paciente "
                "SET nombres = %s, apellidos = %s "
                "WHERE id = %s",
                ["PlainOldName", "PlainOldLast", str(p.pk)],
            )
        # Leer desde el ORM: from_db_value debe tolerar InvalidToken
        p.refresh_from_db()
        # Tolerancia: devuelve el valor tal cual (no rompe)
        self.assertEqual(p.nombres, "PlainOldName")

    def test_actualizar_recifra_datos_legacy(self):
        p = crear_paciente(
            nombres="Viejo",
            apellidos="Plain",
            usuario=self.usuario,
        )
        # Insertar plaintext legacy
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE pacientes_paciente "
                "SET nombres = %s WHERE id = %s",
                ["ViejoPlain", str(p.pk)],
            )
        # Releer (tolerado), modificar, guardar → se cifra
        p.refresh_from_db()
        p.nombres = "NuevoCifrado"
        p.save()
        # Verificar que en BD ahora está cifrado
        with connection.cursor() as cur:
            cur.execute(
                "SELECT nombres FROM pacientes_paciente WHERE id = %s",
                [str(p.pk)],
            )
            raw = cur.fetchone()[0]
        self.assertTrue(raw.startswith("gAAAAA"))
        self.assertNotEqual(raw, "NuevoCifrado")
PYEOF

echo "OK: 5 tests de cifrado añadidos"

echo ""
echo "▶ 4. Verificación de imports"
python3 manage.py shell -c "from apps.pacientes import tests; print('OK: tests importan')"

echo ""
echo "▶ 5. Tests de cifrado"
python3 manage.py test apps.pacientes.tests.CifradoCamposPacienteTests -v 2

echo ""
echo "▶ 6. Regresión completa de pacientes"
python3 manage.py test apps.pacientes -v 1 2>&1 | tail -6

echo ""
echo "▶ 7. Regresión global"
python3 manage.py test apps.configuracion apps.reportes apps.inventario \
    apps.derivaciones apps.usuarios apps.triaje apps.organizaciones \
    apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria \
    -v 1 2>&1 | tail -4

echo ""
echo "✅ FASE 11.1 COMPLETADA (cifrado activo)"
