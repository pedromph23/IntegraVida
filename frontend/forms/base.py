"""Clase base para todos los formularios del proyecto.

Auto-aplica validadores según el nombre del campo. Así no hay que
escribir clean_nombre, clean_telefono, etc. en cada ModelForm.

Uso:
    from frontend.forms.base import ValidatedModelForm

    class MiForm(ValidatedModelForm):
        class Meta:
            model = MiModelo
            fields = ["nombre", "telefono", "direccion"]  # ← validados automáticamente
"""
from django import forms

from frontend.validators import (
    validar_cedula,
    validar_codigo,
    validar_coordenadas,
    validar_direccion,
    validar_edad_aproximada,
    validar_estatura_cm,
    validar_nombre_persona,
    validar_peso_kg,
    validar_telefono,
    validar_texto_libre,
)


# Mapa: nombre de campo → validadores a aplicar
DEFAULT_VALIDATORS = {
    # Nombres de personas
    "nombre":      [validar_nombre_persona],
    "nombres":     [validar_nombre_persona],
    "apellido":    [validar_nombre_persona],
    "apellidos":   [validar_nombre_persona],
    "first_name":  [validar_nombre_persona],
    "last_name":   [validar_nombre_persona],
    "parentesco":  [validar_nombre_persona],

    # Contacto
    "telefono":           [validar_telefono],
    "telefono_publico":   [validar_telefono],
    "telefono_contacto":  [validar_telefono],

    # Identidad
    "cedula":     [validar_cedula],
    "codigo":     [validar_codigo],

    # Dirección
    "direccion":  [validar_direccion],

    # Cuerpo (descripción física)
    "estatura_cm":       [validar_estatura_cm],
    "peso_kg":           [validar_peso_kg],
    "edad_aproximada":   [validar_edad_aproximada],
}


class ValidatedModelForm(forms.ModelForm):
    """ModelForm que auto-aplica validadores a los campos conocidos.

    Puedes sobrescribir con `Meta.validators_map` para casos especiales.
    """

    class Meta:
        # Los hijos deben sobrescribir con {campo: [func1, func2]}
        validators_map = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_validadores_por_defecto()
        self._aplicar_validadores_personalizados()

    def _aplicar_validadores_por_defecto(self):
        """Aplica DEFAULT_VALIDATORS a los campos del form."""
        for nombre_campo, validadores in DEFAULT_VALIDATORS.items():
            if nombre_campo in self.fields:
                field = self.fields[nombre_campo]
                # Evitar duplicar si ya los tiene
                for val in validadores:
                    if val not in field.validators:
                        field.validators.append(val)

    def _aplicar_validadores_personalizados(self):
        """Aplica validadores definidos en Meta.validators_map (sobrescribe)."""
        custom_map = getattr(self.Meta, "validators_map", {})
        for nombre_campo, validadores in custom_map.items():
            if nombre_campo in self.fields:
                field = self.fields[nombre_campo]
                for val in validadores:
                    if val not in field.validators:
                        field.validators.append(val)

    def clean(self):
        """Validación cruzada (ej: coordenadas lat/lng)."""
        cleaned = super().clean()
        lat = cleaned.get("lat")
        lng = cleaned.get("lng")
        if lat is not None and lng is not None:
            validar_coordenadas(lat, lng)
        return cleaned
