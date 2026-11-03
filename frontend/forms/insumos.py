"""Formularios del panel para el módulo Inventario (CRUD de catálogo)."""
from django import forms

from apps.inventario.models import Insumo


class InsumoForm(forms.ModelForm):
    """Crear/editar un Insumo del catálogo global.

    Nota: Insumo es global (sin FK a organizacion). Solo ADMIN_PLATAFORMA
    puede editarlo; el permiso se valida en la vista, no aquí.
    """

    class Meta:
        model = Insumo
        fields = [
            "codigo",
            "nombre",
            "categoria",
            "subcategoria",
            "unidad_medida",
            "requiere_lote",
            "requiere_vencimiento",
            "vida_util_dias",
            "stock_minimo_global",
            "activo",
            "notas",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "nombre": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "categoria": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "subcategoria": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "unidad_medida": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "vida_util_dias": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            }),
            "stock_minimo_global": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
                "step": "0.001",
            }),
            "notas": forms.Textarea(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
                "rows": 3,
            }),
        }
