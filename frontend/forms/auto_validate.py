"""Monkey-patch global: aplica validadores a TODOS los ModelForm.

Instalado desde frontend/apps.py.ready().

Cualquier ModelForm del proyecto (panel, admin, forms futuros) recibirá
automáticamente los validadores de frontend.validators según el nombre
del campo.

Para saltarse la validación en un campo específico:
    class Meta:
        model = MiModelo
        fields = ["nombre", "notas"]
        skip_validators = ["nombre"]   # ← excepción
"""
from django import forms

from frontend.forms.base import DEFAULT_VALIDATORS


def _aplicar_validadores(form_instance):
    """Aplica los validadores a los campos del form_instance."""
    # Verificar si el form pidió excepciones
    skip = getattr(getattr(form_instance, "Meta", None), "skip_validators", [])
    for nombre_campo, validadores in DEFAULT_VALIDATORS.items():
        if nombre_campo in skip:
            continue
        if nombre_campo in form_instance.fields:
            field = form_instance.fields[nombre_campo]
            for val in validadores:
                if val not in field.validators:
                    field.validators.append(val)


def install_auto_validators():
    """Parchea forms.ModelForm.__init__ para auto-aplicar validadores."""
    original_init = forms.ModelForm.__init__

    if getattr(original_init, "_iv_patched", False):
        return  # Ya instalado

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _aplicar_validadores(self)

    patched_init._iv_patched = True
    forms.ModelForm.__init__ = patched_init
