"""Formularios para el CRUD clínico (Pacientes, Episodios, Contactos)."""
from django import forms
from frontend.forms.base import ValidatedModelForm
from apps.hospitales.models import Hospital
from apps.refugios.models import Refugio
from apps.pacientes.models import Paciente, Episodio, ContactoEmergencia
from frontend.validators import (
    validar_cedula, validar_edad_aproximada, validar_estatura_cm,
    validar_nombre_persona, validar_peso_kg, validar_telefono,
)

class PacienteCreateForm(ValidatedModelForm):
    class Meta:
        model = Paciente
        fields = (
            "nombres", "apellidos", "cedula", "fecha_nacimiento", "sexo_biologico",
            "telefono", "email", "notas_internas",
            "color_piel", "color_ojos", "tipo_cara", "estatura_cm", "peso_kg", "edad_aproximada",
        )
        widgets = {
            f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
            for f in ("nombres", "apellidos", "cedula", "telefono", "email")
        }
        widgets["fecha_nacimiento"] = forms.DateInput(attrs={"type": "date", "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["sexo_biologico"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["notas_internas"] = forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 3})
        widgets["color_piel"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["color_ojos"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["tipo_cara"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["estatura_cm"] = forms.NumberInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["peso_kg"] = forms.NumberInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "step": "0.01"})
        widgets["edad_aproximada"] = forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "placeholder": "Ej: 30-40, menor, adulto mayor"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sexo_biologico"].label = "Sexo"
        choices = self.fields["sexo_biologico"].choices
        self.fields["sexo_biologico"].choices = [
            (val, label) for val, label in choices
            if "intersexual" not in label.lower()
        ]

    def clean_nombres(self):
        v = self.cleaned_data.get("nombres", "")
        validar_nombre_persona(v)
        return v

    def clean_apellidos(self):
        v = self.cleaned_data.get("apellidos", "")
        validar_nombre_persona(v)
        return v

    def clean_cedula(self):
        v = self.cleaned_data.get("cedula", "")
        validar_cedula(v)
        return v.strip().upper() if v else v

    def clean_telefono(self):
        v = self.cleaned_data.get("telefono", "")
        validar_telefono(v)
        return v.strip() if v else v

    def clean_estatura_cm(self):
        v = self.cleaned_data.get("estatura_cm")
        validar_estatura_cm(v)
        return v

    def clean_peso_kg(self):
        v = self.cleaned_data.get("peso_kg")
        validar_peso_kg(v)
        return v

    def clean_edad_aproximada(self):
        v = self.cleaned_data.get("edad_aproximada", "")
        validar_edad_aproximada(v)
        return v


class EpisodioForm(ValidatedModelForm):
    class Meta:
        model = Episodio
        fields = ("hospital", "refugio", "motivo_consulta", "notas_internas")
        widgets = {
            "hospital": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "refugio": forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "motivo_consulta": forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 3}),
            "notas_internas": forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 2}),
        }
    def __init__(self, *args, **kwargs):
        org_ids = kwargs.pop("org_ids", [])
        super().__init__(*args, **kwargs)
        self.fields["hospital"].queryset = Hospital.objects.filter(organizacion_id__in=org_ids).order_by("nombre")
        self.fields["refugio"].queryset = Refugio.objects.filter(organizacion_id__in=org_ids).order_by("nombre")
        self.fields["hospital"].required = False
        self.fields["refugio"].required = False

    def clean(self):
        cleaned = super().clean()
        h, r = cleaned.get("hospital"), cleaned.get("refugio")
        if bool(h) == bool(r):
            raise forms.ValidationError("Debe seleccionar exactamente un Hospital o un Refugio, no ambos ni ninguno.")
        return cleaned

class ContactoEmergenciaForm(ValidatedModelForm):
    class Meta:
        model = ContactoEmergencia
        fields = ("nombre", "parentesco", "telefono", "es_principal")
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "parentesco": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "telefono": forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}),
            "es_principal": forms.CheckboxInput(attrs={"class": "rounded border-border"}),
        }

    def clean_nombre(self):
        v = self.cleaned_data.get("nombre", "")
        validar_nombre_persona(v)
        return v

    def clean_parentesco(self):
        v = self.cleaned_data.get("parentesco", "")
        if v and len(v) > 50:
            from django.core.exceptions import ValidationError
            raise ValidationError("El parentesco no puede superar 50 caracteres.")
        return v

    def clean_telefono(self):
        v = self.cleaned_data.get("telefono", "")
        validar_telefono(v)
        return v.strip() if v else v

