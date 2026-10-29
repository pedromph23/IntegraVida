#!/usr/bin/env python3
"""Fix: calcular_hash debe serializar UUIDs (objeto_id, metadatos)."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

def patch(path, old, new, label=""):
    p = BASE / path
    if not p.exists():
        sys.exit(f"ERROR: no existe {path}")
    text = p.read_text(encoding="utf-8")
    if old not in text and new in text:
        print(f"  ya aplicado: {label}")
        return
    n = text.count(old)
    if n != 1:
        sys.exit(f"ERROR: {path} — '{old[:50]}...' aparece {n} veces")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label}")

print("== Fix calcular_hash (UUID-safe) ==")

# 1) Insertar helper _json_default ANTES de def calcular_hash
patch(
    "apps/auditoria/models.py",
    "def calcular_hash(evento):\n",
    'def _json_default(o):\n'
    '    """Serializador de respaldo para json.dumps: UUID → str."""\n'
    '    if isinstance(o, uuid.UUID):\n'
    '        return str(o)\n'
    '    raise TypeError(\n'
    '        f"Object of type {o.__class__.__name__} is not JSON serializable"\n'
    '    )\n'
    '\n'
    '\n'
    'def calcular_hash(evento):\n',
    "helper _json_default insertado"
)

# 2) objeto_id → str explícito
patch(
    "apps/auditoria/models.py",
    '        "objeto_id": evento.objeto_id,\n',
    '        "objeto_id": str(evento.objeto_id) if evento.objeto_id else "",\n',
    "objeto_id str()"
)

# 3) json.dumps con default=_json_default
patch(
    "apps/auditoria/models.py",
    '    serialized = json.dumps(\n'
    '        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")\n'
    '    )\n',
    '    serialized = json.dumps(\n'
    '        payload,\n'
    '        sort_keys=True,\n'
    '        ensure_ascii=False,\n'
    '        separators=(",", ":"),\n'
    '        default=_json_default,\n'
    '    )\n',
    "json.dumps: default=_json_default"
)

print("\n✅ Fix UUID aplicado. Ejecuta: python manage.py test apps.emergencias apps.auditoria -v 2")
