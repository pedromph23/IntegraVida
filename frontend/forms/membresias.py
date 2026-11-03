"""Formularios del panel para Membresías."""
from django import forms

from apps.organizaciones.models import Membresia


class MembresiaForm(forms.ModelForm):
    """Crear una membresía. La vista filtra organizaciones visibles."""

    class Meta:
        model = Membresia
        fields = ["usuario", "organizacion", "rol", "estado", "ambito_municipio"]
        widgets = {
            "usuario": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "organizacion": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "rol": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "estado": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "ambito_municipio": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
        }
