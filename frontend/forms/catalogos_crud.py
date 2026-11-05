"""Formularios del panel para catálogos de plataforma.

Incluye validaciones robustas (frontend/validators.py) para evitar
datos basura en organizaciones, entidades, municipios y parroquias.
"""
import re

from django import forms
from frontend.forms.base import ValidatedModelForm

from apps.organizaciones.models import Organizacion
from apps.territorio.models import EntidadFederal, Municipio, Parroquia
from frontend.validators import validar_codigo, validar_telefono


class OrganizacionForm(ValidatedModelForm):
    class Meta:
        model = Organizacion
        fields = (
            "codigo", "nombre", "tipo", "estado",
            "descripcion", "telefono_publico", "correo_publico",
        )
        widgets = {
            f: forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            })
            for f in ("codigo", "nombre", "telefono_publico", "correo_publico")
        }
        widgets["tipo"] = forms.Select(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
        })
        widgets["estado"] = forms.Select(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
        })
        widgets["descripcion"] = forms.Textarea(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            "rows": 3,
        })

    def clean_codigo(self):
        v = self.cleaned_data.get("codigo", "")
        validar_codigo(v)
        return v.strip().lower() if v else v

    def clean_nombre(self):
        v = self.cleaned_data.get("nombre", "").strip()
        if len(v) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if len(v) > 180:
            raise forms.ValidationError("El nombre no puede superar 180 caracteres.")
        if not re.match(r"^[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ .,'()&-]+$", v):
            raise forms.ValidationError(
                "El nombre contiene caracteres no permitidos "
                "(solo letras, números y . , ' ( ) & -)."
            )
        return v

    def clean_telefono_publico(self):
        v = self.cleaned_data.get("telefono_publico", "")
        validar_telefono(v)
        return v.strip() if v else v

    def clean_descripcion(self):
        v = self.cleaned_data.get("descripcion", "").strip()
        if v and len(v) > 1000:
            raise forms.ValidationError("La descripción no puede superar 1000 caracteres.")
        return v


class EntidadFederalForm(ValidatedModelForm):
    class Meta:
        model = EntidadFederal
        fields = ("codigo", "nombre", "tipo", "activa")
        widgets = {
            f: forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            })
            for f in ("codigo", "nombre")
        }

    def clean_codigo(self):
        v = self.cleaned_data.get("codigo", "")
        validar_codigo(v)
        return v.strip().upper() if v else v

    def clean_nombre(self):
        v = self.cleaned_data.get("nombre", "").strip()
        if len(v) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if len(v) > 120:
            raise forms.ValidationError("El nombre no puede superar 120 caracteres.")
        return v


class MunicipioForm(ValidatedModelForm):
    class Meta:
        model = Municipio
        fields = ("entidad_federal", "codigo", "nombre", "activo")
        widgets = {
            f: forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            })
            for f in ("codigo", "nombre")
        }
        widgets["entidad_federal"] = forms.Select(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
        })

    def clean_codigo(self):
        v = self.cleaned_data.get("codigo", "")
        validar_codigo(v)
        return v.strip().upper() if v else v

    def clean_nombre(self):
        v = self.cleaned_data.get("nombre", "").strip()
        if len(v) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if len(v) > 120:
            raise forms.ValidationError("El nombre no puede superar 120 caracteres.")
        return v


class ParroquiaForm(ValidatedModelForm):
    class Meta:
        model = Parroquia
        fields = ("municipio", "codigo", "nombre", "activa")
        widgets = {
            f: forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
            })
            for f in ("codigo", "nombre")
        }
        widgets["municipio"] = forms.Select(attrs={
            "class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface",
        })

    def clean_codigo(self):
        v = self.cleaned_data.get("codigo", "")
        validar_codigo(v)
        return v.strip().upper() if v else v

    def clean_nombre(self):
        v = self.cleaned_data.get("nombre", "").strip()
        if len(v) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if len(v) > 120:
            raise forms.ValidationError("El nombre no puede superar 120 caracteres.")
        return v
