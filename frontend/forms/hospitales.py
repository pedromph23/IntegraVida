"""Formularios del panel para el módulo Hospitales (F5.b)."""
from django import forms

from apps.hospitales.models import Hospital
from apps.usuarios.permisos import ACCION_CREAR, orgs_donde_puede


class HospitalForm(forms.ModelForm):
    """Crear / editar Hospital.

    - `organizacion` se filtra a las orgs donde el user puede CREAR.
    - En UPDATE: organizacion disabled, codigo fuera del form
      (identificador inmutable).
    - `ubicacion` (PointField) se omite: requiere editor de mapa.
    - `servicios` (M2M) se gestiona en el detalle (F5.d), no en este form.
    """

    class Meta:
        model = Hospital
        fields = [
            "organizacion",
            "codigo",
            "nombre",
            "tipo",
            "nivel",
            "direccion",
            "referencia_lugar",
            "telefono_publico",
            "correo_publico",
            "notas_internas",
        ]
        widgets = {
            "organizacion": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "codigo": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface font-mono",
                "placeholder": "ej. hospital-central-caracas",
            }),
            "nombre": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "tipo": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "nivel": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "direccion": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "referencia_lugar": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "telefono_publico": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "placeholder": "+58 412-000-0000",
            }),
            "correo_publico": forms.EmailInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "notas_internas": forms.Textarea(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "rows": 3,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user is None:
            return

        orgs = orgs_donde_puede(user, "hospitales", ACCION_CREAR)
        self.fields["organizacion"].queryset = orgs

        if orgs.count() == 1:
            self.fields["organizacion"].initial = orgs.first()

        is_update = self.instance is not None and not self.instance._state.adding
        if is_update:
            self.fields["organizacion"].disabled = True
            self.fields.pop("codigo", None)
