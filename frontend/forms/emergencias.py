"""Formularios del panel para el módulo Emergencias (F5.c)."""
from django import forms

from apps.emergencias.models import Emergencia
from frontend.validators import validar_texto_libre
from apps.usuarios.permisos import ACCION_CREAR, orgs_donde_puede


class EmergenciaForm(forms.ModelForm):
    """Crear / editar Emergencia.

    - `estado` NO está aquí: se gestiona con la acción "cambiar estado".
    - `punto` (PointField) se omite: requiere editor de mapa.
    - `reportada_por` se setea a request.user en create (si vacío).
    - En UPDATE, no se puede mover de organización.
    """

    class Meta:
        model = Emergencia
        fields = [
            "organizacion",
            "titulo",
            "descripcion",
            "categoria",
            "gravedad",
            "ubicacion_texto",
            "referencia_lugar",
        ]
        widgets = {
            "organizacion": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "titulo": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "placeholder": "ej. Inundación en Petare",
            }),
            "descripcion": forms.Textarea(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "rows": 4,
            }),
            "categoria": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "gravedad": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "ubicacion_texto": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "placeholder": "ej. Av. Francisco de Miranda, Caracas",
            }),
            "referencia_lugar": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "placeholder": "Punto de referencia opcional",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user is None:
            return

        orgs = orgs_donde_puede(user, "emergencias", ACCION_CREAR)
        self.fields["organizacion"].queryset = orgs
        self.fields["organizacion"].required = False  # puede ser null

        if orgs.count() == 1:
            self.fields["organizacion"].initial = orgs.first()

        is_update = self.instance is not None and not self.instance._state.adding
        if is_update:
            self.fields["organizacion"].disabled = True

    def clean_titulo(self):
        v = self.cleaned_data.get("titulo", "")
        validar_texto_libre(v, min_len=5, max_len=200, campo="El título")
        return v

    def clean_descripcion(self):
        v = self.cleaned_data.get("descripcion", "")
        validar_texto_libre(v, min_len=10, max_len=2000, campo="La descripción")
        return v
