#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

python3 - << 'PY'
from pathlib import Path

sp = Path("apps/reportes/services.py")
text = sp.read_text(encoding="utf-8")

old = '''def _validar_organizacion(usuario, organizacion):
    if organizacion is None:
        if puede_administrar_plataforma(usuario):
            return
        raise ValidationError(
            {"organizacion": "Debes especificar una organización."}
        )
    if not tiene_acceso_a_organizacion(usuario, organizacion):
        raise PermissionDenied(
            "No tienes acceso a esa organización."
        )
'''

new = '''def _validar_organizacion(usuario, organizacion):
    """Sin organizacion = agregar sobre las visibles del usuario.

    Con organizacion = exigir acceso explícito.
    """
    if organizacion is None:
        if not _organizaciones_visibles(usuario).exists():
            raise ValidationError(
                {"organizacion": "No tienes organizaciones visibles."}
            )
        return
    if not tiene_acceso_a_organizacion(usuario, organizacion):
        raise PermissionDenied(
            "No tienes acceso a esa organización."
        )
'''

if old in text:
    text = text.replace(old, new, 1)
    sp.write_text(text, encoding="utf-8")
    print("OK: _validar_organizacion permite sin org si hay visibles")
else:
    print("ERROR: patrón no encontrado en services.py")
PY

echo ""
echo "▶ Verificación"
python3 manage.py shell -c "from apps.reportes import services; print('OK: services importan')"
