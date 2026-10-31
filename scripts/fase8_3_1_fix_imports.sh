#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

python3 - << 'PY'
from pathlib import Path

# ── Fix 1: timezone en models.py ──────────────────────────────────
mp = Path("apps/inventario/models.py")
text = mp.read_text(encoding="utf-8")

if "from django.utils import timezone" not in text:
    old = (
        "from django.contrib.gis.db import models as gis_models\n"
        "from django.db import models\n"
    )
    new = (
        "from django.contrib.gis.db import models as gis_models\n"
        "from django.db import models\n"
        "from django.utils import timezone\n"
    )
    if old in text:
        text = text.replace(old, new, 1)
        mp.write_text(text, encoding="utf-8")
        print("OK: timezone importado en models.py")
    else:
        print("ERROR: marker de imports no encontrado en models.py")
else:
    print("ya aplicado: timezone en models.py")

# ── Fix 2: PermissionDenied en services.py ────────────────────────
sp = Path("apps/inventario/services.py")
text = sp.read_text(encoding="utf-8")

if "from django.core.exceptions import PermissionDenied" not in text:
    old = "from django.core.exceptions import ValidationError\n"
    new = (
        "from django.core.exceptions import PermissionDenied, ValidationError\n"
    )
    if old in text:
        text = text.replace(old, new, 1)
        sp.write_text(text, encoding="utf-8")
        print("OK: PermissionDenied importado en services.py")
    else:
        print("ERROR: marker de imports no encontrado en services.py")
else:
    print("ya aplicado: PermissionDenied en services.py")
PY

echo ""
echo "▶ Verificar imports"
python3 -c "from apps.inventario import models, services; print('OK: módulos importan sin error')"
