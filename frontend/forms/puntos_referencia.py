"""Formulario para crear/editar PuntoReferencia."""
from django import forms
from django.contrib.gis.geos import Point

from apps.refugios.models import PuntoReferencia


class PuntoReferenciaForm(forms.ModelForm):
    lat = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            "step": "0.000001", "placeholder": "Ej: 10.4806",
        }),
        help_text="Latitud (decimal).",
    )
    lng = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            "step": "0.000001", "placeholder": "Ej: -66.9036",
        }),
        help_text="Longitud (decimal).",
    )

    class Meta:
        model = PuntoReferencia
        fields = ["nombre", "categoria", "direccion", "telefono", "notas", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "categoria": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "direccion": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "telefono": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "notas": forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "rounded border-border"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.ubicacion:
            self.fields["lat"].initial = self.instance.ubicacion.y
            self.fields["lng"].initial = self.instance.ubicacion.x

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.ubicacion = Point(
            self.cleaned_data["lng"], self.cleaned_data["lat"], srid=4326,
        )
        if commit:
            instance.save()
        return instance
