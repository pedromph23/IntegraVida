from django.contrib import admin

from .models import EntidadFederal, Municipio, Parroquia


@admin.register(EntidadFederal)
class EntidadFederalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "tipo", "activa")
    list_filter = ("tipo", "activa")
    search_fields = ("nombre", "codigo")
    ordering = ("nombre",)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "entidad_federal", "activo")
    list_filter = ("entidad_federal", "activo")
    search_fields = ("nombre", "codigo", "entidad_federal__nombre")
    autocomplete_fields = ("entidad_federal",)
    ordering = ("entidad_federal__nombre", "nombre")


@admin.register(Parroquia)
class ParroquiaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "municipio", "activa")
    list_filter = ("municipio__entidad_federal", "activa")
    search_fields = (
        "nombre",
        "codigo",
        "municipio__nombre",
        "municipio__entidad_federal__nombre",
    )
    autocomplete_fields = ("municipio",)
    ordering = ("municipio__entidad_federal__nombre", "municipio__nombre", "nombre")
