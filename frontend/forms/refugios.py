"""Formularios del panel para el módulo Refugios (F5.a)."""
from django import forms

from apps.refugios.models import Refugio
from apps.usuarios.permisos import ACCION_CREAR, orgs_donde_puede


class RefugioForm(forms.ModelForm):
    """Crear / editar Refugio.

    - `organizacion` se filtra a las orgs donde el user tiene CREAR.
    - En edición, `organizacion` se deshabilita (no se puede mover de org).
    - `codigo` único se valida automáticamente (SlugField unique=True).
    """

    class Meta:
        model = Refugio
        fields = [
            "organizacion",
            "codigo",
            "nombre",
            "tipo",
            "direccion",
            "capacidad_total",
            "telefono_publico",
            "correo_publico",
        ]
        widgets = {
            "organizacion": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "codigo": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface font-mono",
                "placeholder": "ej. refugio-caracas-01",
            }),
            "nombre": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "tipo": forms.Select(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "direccion": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
            }),
            "capacidad_total": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 "
                         "text-sm bg-surface",
                "min": 0,
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
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if user is None:
            return

        # Organizaciones donde el user puede crear refugios
        orgs = orgs_donde_puede(user, "refugios", ACCION_CREAR)
        self.fields["organizacion"].queryset = orgs

        # Si el user solo ve 1 org → preseleccionar (no mostrar select vacío)
        if orgs.count() == 1:
            self.fields["organizacion"].initial = orgs.first()
            self.fields["organizacion"].widget.attrs["readonly"] = True

        # Detectar UPDATE con _state.adding (pk puede ser UUID generado
        # en CREATE, making self.instance.pk truthy sin estar en DB).
        is_update = self.instance is not None and not self.instance._state.adding

        if is_update:
            # organizacion: no se puede mover de org.
            # codigo: identificador inmutable → fuera del form.
            self.fields["organizacion"].disabled = True
            self.fields.pop("codigo", None)
