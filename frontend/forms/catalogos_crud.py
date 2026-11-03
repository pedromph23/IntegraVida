from django import forms
from apps.organizaciones.models import Organizacion
from apps.territorio.models import EntidadFederal, Municipio, Parroquia

class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ("codigo", "nombre", "tipo", "estado", "descripcion", "telefono_publico", "correo_publico")
        widgets = {
            f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
            for f in ("codigo", "nombre", "telefono_publico", "correo_publico")
        }
        widgets["tipo"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["estado"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
        widgets["descripcion"] = forms.Textarea(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface", "rows": 3})

class EntidadFederalForm(forms.ModelForm):
    class Meta:
        model = EntidadFederal
        fields = ("codigo", "nombre", "tipo", "activa")
        widgets = {f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}) for f in ("codigo", "nombre")}

class MunicipioForm(forms.ModelForm):
    class Meta:
        model = Municipio
        fields = ("entidad_federal", "codigo", "nombre", "activo")
        widgets = {f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}) for f in ("codigo", "nombre")}
        widgets["entidad_federal"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})

class ParroquiaForm(forms.ModelForm):
    class Meta:
        model = Parroquia
        fields = ("municipio", "codigo", "nombre", "activa")
        widgets = {f: forms.TextInput(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"}) for f in ("codigo", "nombre")}
        widgets["municipio"] = forms.Select(attrs={"class": "w-full rounded-lg border border-border px-3 py-2 text-sm bg-surface"})
