"""Formularios del panel para Usuarios (creación con membresía inicial)."""
from django import forms
from frontend.forms.base import ValidatedModelForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from apps.organizaciones.models import Membresia
from frontend.validators import validar_nombre_persona, validar_telefono

User = get_user_model()


class UsuarioCreateForm(UserCreationForm):
    """Crea un User y su primera Membresía en la organización elegida."""

    organizacion = forms.ModelChoiceField(
        queryset=Membresia.objects.none(),  # se inyecta en la vista
        label="Organización",
        required=True,
    )
    rol = forms.ChoiceField(
        choices=Membresia.Rol.choices,
        initial="OPERADOR",
        label="Rol en la organización",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "telefono")

    def clean_username(self):
        v = self.cleaned_data.get("username", "").strip()
        import re
        if not re.match(r"^[A-Za-z0-9_.-]{3,30}$", v):
            from django.core.exceptions import ValidationError
            raise ValidationError(
                "El usuario debe tener 3-30 caracteres: letras, números, "
                "puntos, guiones o guiones bajos."
            )
        return v

    def clean_first_name(self):
        v = self.cleaned_data.get("first_name", "")
        validar_nombre_persona(v)
        return v

    def clean_last_name(self):
        v = self.cleaned_data.get("last_name", "")
        validar_nombre_persona(v)
        return v

    def clean_telefono(self):
        v = self.cleaned_data.get("telefono", "")
        validar_telefono(v)
        return v.strip() if v else v


    def __init__(self, *args, **kwargs):
        orgs_qs = kwargs.pop("orgs_qs", None)
        super().__init__(*args, **kwargs)
        if orgs_qs is not None:
            self.fields["organizacion"].queryset = orgs_qs
        for f in self.fields.values():
            f.widget.attrs.setdefault(
                "class",
                "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            )


class UsuarioUpdateForm(ValidatedModelForm):
    """Edita datos personales (no credenciales ni membresías)."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "telefono")

    def clean_first_name(self):
        v = self.cleaned_data.get("first_name", "")
        validar_nombre_persona(v)
        return v

    def clean_last_name(self):
        v = self.cleaned_data.get("last_name", "")
        validar_nombre_persona(v)
        return v

    def clean_telefono(self):
        v = self.cleaned_data.get("telefono", "")
        validar_telefono(v)
        return v.strip() if v else v


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault(
                "class",
                "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            )
