#!/usr/bin/env python3
"""Fase 6.3.1 — Fix estructural de Usuario.email."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def patch(rel, old, new, label):
    p = BASE / rel
    if not p.exists():
        sys.exit(f"ERROR: no existe {rel}")
    text = p.read_text(encoding="utf-8")
    if old not in text and new in text:
        print(f"  ya aplicado: {label}")
        return
    if text.count(old) != 1:
        sys.exit(f"ERROR: {rel} — patrón {text.count(old)} veces ({label})")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label}")

print("== 1/2: Cambiar email a blank=True sin unique en el campo ==")
patch(
    "apps/usuarios/models.py",
    '    email = models.EmailField("correo electrónico", unique=True)\n',
    '    email = models.EmailField("correo electrónico", blank=True)\n',
    "email: blank=True, sin unique"
)

print("== 2/2: Añadir UniqueConstraint condicional en Meta ==")
patch(
    "apps/usuarios/models.py",
    "        ordering = [\"username\"]\n",
    "        ordering = [\"username\"]\n"
    "        constraints = [\n"
    "            models.UniqueConstraint(\n"
    "                fields=[\"email\"],\n"
    "                condition=~models.Q(email=\"\"),\n"
    "                name=\"unique_usuario_email_nonempty\",\n"
    "            ),\n"
    "        ]\n",
    "Meta.constraints: unique condicional email no vacío"
)

print("\n✅ Modelo parcheado. Siguiente paso:")
print("   python manage.py makemigrations usuarios")
print("   python manage.py migrate usuarios")
