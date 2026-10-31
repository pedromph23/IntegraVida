#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Añadir EncryptedTextField a fields.py"
python3 - << 'PY'
from pathlib import Path
p = Path("apps/pacientes/fields.py")
text = p.read_text(encoding="utf-8")
if "class EncryptedTextField" not in text:
    text = text.rstrip() + (
        "\n\nclass EncryptedTextField(EncryptedFieldMixin, models.TextField):\n"
        '    """TextField que cifra el valor en la base de datos."""\n'
        "    pass\n"
    )
    p.write_text(text, encoding="utf-8")
    print("OK: EncryptedTextField añadido")
else:
    print("ya aplicado: EncryptedTextField")
PY

echo ""
echo "▶ 2. Patch Paciente model"
python3 - << 'PY'
from pathlib import Path
p = Path("apps/pacientes/models.py")
text = p.read_text(encoding="utf-8")

if "from apps.pacientes.fields import" not in text:
    needle = "from django.utils import timezone\n"
    if needle not in text:
        raise SystemExit("ERROR: marker 'from django.utils import timezone' no encontrado")
    text = text.replace(
        needle,
        needle + "\nfrom apps.pacientes.fields import (\n"
        "    EncryptedCharField, EncryptedEmailField, EncryptedTextField,\n"
        ")\n",
        1,
    )
    print("OK: import añadido")

repls = [
    ('    cedula = models.CharField(max_length=20, blank=True, default="")',
     '    cedula = EncryptedCharField(max_length=500, blank=True, default="")'),
    ('    nombres = models.CharField(max_length=200)',
     '    nombres = EncryptedCharField(max_length=500)'),
    ('    apellidos = models.CharField(max_length=200)',
     '    apellidos = EncryptedCharField(max_length=500)'),
    ('    telefono = models.CharField(max_length=30, blank=True)',
     '    telefono = EncryptedCharField(max_length=500, blank=True)'),
    ('    email = models.EmailField(blank=True)',
     '    email = EncryptedEmailField(blank=True, max_length=500)'),
    ('    notas_internas = models.TextField(blank=True)',
     '    notas_internas = EncryptedTextField(blank=True)'),
]
for old, new in repls:
    if new in text:
        print(f"ya aplicado: {new.strip()[:60]}")
        continue
    if old not in text:
        raise SystemExit(f"ERROR: no se encontró '{old}'")
    text = text.replace(old, new, 1)
    print(f"OK: {old.strip()[:45]}...")

p.write_text(text, encoding="utf-8")
PY

echo ""
echo "▶ 3. makemigrations pacientes"
python3 manage.py makemigrations pacientes

echo ""
echo "▶ 4. Ver contenido de la migración generada"
MIG=$(ls -1 apps/pacientes/migrations/0002_*.py 2>/dev/null | head -1)
if [ -z "$MIG" ]; then
    echo "ERROR: no se generó migración 0002"
    exit 1
fi
echo "Migración: $MIG"
echo "────────────────────────────────────────"
cat "$MIG"
echo "────────────────────────────────────────"

echo ""
echo "▶ 5. manage.py check"
python3 manage.py check

echo ""
echo "✅ Fase 11.1.models completada (SIN aplicar migración)"
echo ""
echo "Siguiente paso: revisar la migración arriba y aplicar con migrate."
