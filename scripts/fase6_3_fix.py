#!/usr/bin/env python3
"""Fix de bugs de Fase 6.3: FOR UPDATE + Usuario.email unique."""
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
        sys.exit(f"ERROR: {rel} — patrón {text.count(old)} veces (label={label})")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"  OK: {label}")

# ══════════════════════════════════════════════════════════════════
# FIX 1 — services.py: select_for_update(of=("self",))
# ══════════════════════════════════════════════════════════════════
print("== FIX 1: select_for_update en triaje/services.py ==")
patch(
    "apps/triaje/services.py",
    "        episodio = (\n"
    "            Episodio.objects\n"
    "            .select_for_update()\n"
    "            .select_related(\"paciente\", \"hospital\", \"refugio\")\n"
    "            .get(pk=episodio_id)\n"
    "        )\n",
    "        episodio = (\n"
    "            Episodio.objects\n"
    "            .select_for_update(of=(\"self\",))\n"
    "            .get(pk=episodio_id)\n"
    "        )\n",
    "select_for_update(of=('self',)) sin select_related nullable"
)

# ══════════════════════════════════════════════════════════════════
# FIX 2 — organizaciones/tests.py: emails únicos
# ══════════════════════════════════════════════════════════════════
print("== FIX 2: emails únicos en tests ==")
patch(
    "apps/organizaciones/tests.py",
    '        cls.usuario_sin = Usuario.objects.create_user(\n'
    '            username="sin-ambito", password="x"\n'
    '        )\n'
    '        cls.usuario_con = Usuario.objects.create_user(\n'
    '            username="con-ambito", password="x"\n'
    '        )\n',
    '        cls.usuario_sin = Usuario.objects.create_user(\n'
    '            username="sin-ambito", email="sin-ambito@test.local", password="x"\n'
    '        )\n'
    '        cls.usuario_con = Usuario.objects.create_user(\n'
    '            username="con-ambito", email="con-ambito@test.local", password="x"\n'
    '        )\n',
    "AmbitoMembresiaTests: emails únicos"
)

# ══════════════════════════════════════════════════════════════════
# FIX 3 — pacientes/tests.py: emails únicos en FiltradoEpisodiosPorAmbitoTests
# ══════════════════════════════════════════════════════════════════
patch(
    "apps/pacientes/tests.py",
    '        cls.usuario_operador = Usuario.objects.create_user(\n'
    '            username="amb-op", password="x"\n'
    '        )\n'
    '        cls.usuario_sin = Usuario.objects.create_user(\n'
    '            username="amb-sin", password="x"\n'
    '        )\n'
    '        cls.superuser = Usuario.objects.create_user(\n'
    '            username="amb-super", password="x", is_superuser=True\n'
    '        )\n',
    '        cls.usuario_operador = Usuario.objects.create_user(\n'
    '            username="amb-op", email="amb-op@test.local", password="x"\n'
    '        )\n'
    '        cls.usuario_sin = Usuario.objects.create_user(\n'
    '            username="amb-sin", email="amb-sin@test.local", password="x"\n'
    '        )\n'
    '        cls.superuser = Usuario.objects.create_user(\n'
    '            username="amb-super", email="amb-super@test.local",\n'
    '            password="x", is_superuser=True\n'
    '        )\n',
    "FiltradoEpisodiosPorAmbitoTests: emails únicos"
)

# ══════════════════════════════════════════════════════════════════
# FIX 4 — triaje/tests.py: emails únicos
# ══════════════════════════════════════════════════════════════════
patch(
    "apps/triaje/tests.py",
    '    usuario = Usuario.objects.create_user(username="triage-u", password="x")\n',
    '    usuario = Usuario.objects.create_user(\n'
    '        username="triage-u", email="triage-u@test.local", password="x"\n'
    '    )\n',
    "TriajeTests helper _setup_basico: email único"
)

patch(
    "apps/triaje/tests.py",
    '        usuario_ajeno = Usuario.objects.create_user(\n'
    '            username="triage-ajeno", password="x"\n'
    '        )\n',
    '        usuario_ajeno = Usuario.objects.create_user(\n'
    '            username="triage-ajeno", email="triage-ajeno@test.local",\n'
    '            password="x"\n'
    '        )\n',
    "test_sin_acceso_falla: email único"
)

print("\n✅ Fixes aplicados.")
print("Nota: Usuario.email=unique es un bug de diseño que debe revisarse.")
print("      Ver mensaje del asistente para propuesta de fix estructural.")
