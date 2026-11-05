"""Formularios para Servicios, Recursos, Almacenes y Lotes."""
from django import forms
from frontend.forms.base import ValidatedModelForm
from apps.hospitales.models import Servicio, RecursoHospitalario
from apps.inventario.models import Almacen, Lote

class ServicioForm(ValidatedModelForm):
    class Meta:
        model = Servicio
        fields = ("codigo", "nombre", "tipo", "activo")
        widgets = {f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}) for f in ("codigo", "nombre")}
        widgets["tipo"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["activo"] = forms.CheckboxInput(attrs={"class": "rounded border-border"})

class RecursoHospitalarioForm(ValidatedModelForm):
    class Meta:
        model = RecursoHospitalario
        fields = ("tipo", "capacidad_total", "disponible")
        widgets = {
            "tipo": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "capacidad_total": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "disponible": forms.NumberInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
        }

class AlmacenForm(ValidatedModelForm):
    class Meta:
        model = Almacen
        fields = ("codigo", "nombre", "hospital", "refugio", "direccion", "activo", "notas")
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "nombre": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "hospital": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "refugio": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "direccion": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "notas": forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 2}),
        }
    def clean(self):
        cleaned = super().clean()
        if bool(cleaned.get("hospital")) == bool(cleaned.get("refugio")):
            raise forms.ValidationError("Debe seleccionar exactamente un Hospital o un Refugio.")
        return cleaned

class LoteForm(ValidatedModelForm):
    class Meta:
        model = Lote
        fields = ("insumo", "codigo", "fecha_vencimiento", "proveedor")
        widgets = {
            "insumo": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "codigo": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "proveedor": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
        }
