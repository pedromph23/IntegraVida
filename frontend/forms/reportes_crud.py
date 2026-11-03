from django import forms
from apps.emergencias.models import ReporteEmergencia

class ReporteEmergenciaForm(forms.ModelForm):
    class Meta:
        model = ReporteEmergencia
        fields = ("categoria", "descripcion", "ubicacion_texto", "referencia_lugar", "municipio", "parroquia", "canal", "estado_revision")
        widgets = {
            "categoria": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "descripcion": forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 3}),
            "ubicacion_texto": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "referencia_lugar": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "municipio": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "parroquia": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "canal": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "estado_revision": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
        }
