"""Formularios del panel para el módulo Inventario (CRUD de catálogo)."""
from django import forms
from frontend.forms.base import ValidatedModelForm

from apps.inventario.models import Insumo
from frontend.validators import validar_codigo


class InsumoForm(ValidatedModelForm):
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

    def clean_codigo(self):
        v = self.cleaned_data.get("codigo", "")
        validar_codigo(v)
        return v.strip().lower() if v else v

    def clean_stock_minimo_global(self):
        v = self.cleaned_data.get("stock_minimo_global")
        if v is not None and v < 0:
            from django.core.exceptions import ValidationError
            raise ValidationError("El stock mínimo no puede ser negativo.")
        return v

    def clean_vida_util_dias(self):
        v = self.cleaned_data.get("vida_util_dias")
        if v is not None and v > 36500:
            from django.core.exceptions import ValidationError
            raise ValidationError("La vida útil no puede superar 100 años (36500 días).")
        return v

