#!/usr/bin/env python3
"""Fase 6.3.1 — tests + docs para el fix de email."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

# ══════════════════════════════════════════════════════════════════
# Tests: usuarios/tests.py (crear o append)
# ══════════════════════════════════════════════════════════════════
tests_path = BASE / "apps" / "usuarios" / "tests.py"
if not tests_path.exists():
    tests_path.write_text("", encoding="utf-8")

existing = tests_path.read_text(encoding="utf-8")

nuevos = '''

# ══════════════════════════════════════════════════════════════════
# Unicidad condicional de email (Fase 6.3.1)
# ══════════════════════════════════════════════════════════════════

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.usuarios.models import Usuario


class EmailUnicidadCondicionalTests(TestCase):
    def test_multiples_usuarios_sin_email(self):
        u1 = Usuario.objects.create_user(username="sin-email-1", password="x")
        u2 = Usuario.objects.create_user(username="sin-email-2", password="x")
        u3 = Usuario.objects.create_user(username="sin-email-3", password="x")
        self.assertEqual(u1.email, "")
        self.assertEqual(u2.email, "")
        self.assertEqual(u3.email, "")
        self.assertEqual(
            Usuario.objects.filter(email="").count(), 3
        )

    def test_dos_usuarios_con_mismo_email_falla(self):
        Usuario.objects.create_user(
            username="con-email-1",
            email="dup@test.local",
            password="x",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create_user(
                    username="con-email-2",
                    email="dup@test.local",
                    password="x",
                )

    def test_email_unico_no_vacio_ok(self):
        u1 = Usuario.objects.create_user(
            username="ok-1", email="a@test.local", password="x"
        )
        u2 = Usuario.objects.create_user(
            username="ok-2", email="b@test.local", password="x"
        )
        self.assertEqual(u1.email, "a@test.local")
        self.assertEqual(u2.email, "b@test.local")
'''

if "class EmailUnicidadCondicionalTests" not in existing:
    tests_path.write_text(existing + nuevos, encoding="utf-8")
    print("  OK: usuarios/tests.py +3 tests")
else:
    print("  ya aplicado: usuarios/tests.py")

# ══════════════════════════════════════════════════════════════════
# Docs: reemplazar nota de bug por nota de fix
# ══════════════════════════════════════════════════════════════════
dd = BASE / "docs" / "data-dictionary.md"
text = dd.read_text(encoding="utf-8")

nota_vieja_marker = "## Nota crítica: `usuarios.Usuario.email`"

if nota_vieja_marker in text:
    # Reemplazar desde el marcador hasta el final del documento
    idx = text.find(nota_vieja_marker)
    texto_antes = text[:idx].rstrip()

    nota_nueva = """

## Nota: `usuarios.Usuario.email` — bug corregido en Fase 6.3.1

**Bug original (Fase 2–6.3):** `EmailField(unique=True)` sin `blank=True`
ni `null=True`. Dos usuarios sin email colisionaban en `""` con
`IntegrityError`.

**Fix aplicado en Fase 6.3.1:**

```python
email = models.EmailField("correo electrónico", blank=True)
# Meta.constraints:
UniqueConstraint(
    fields=["email"],
    condition=~models.Q(email=""),
    name="unique_usuario_email_nonempty",
)
