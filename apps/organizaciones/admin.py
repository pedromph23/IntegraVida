from django.contrib import admin

from .models import Membresia, Organizacion


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "estado",
        "telefono_publico",
        "correo_publico",
    )
    list_filter = ("tipo", "estado")
    search_fields = ("nombre", "codigo", "correo_publico", "telefono_publico")
    readonly_fields = ("id", "creada_en", "actualizada_en")
    ordering = ("nombre",)


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "organizacion",
        "rol",
        "estado",
        "creada_en",
    )
    list_filter = ("rol", "estado", "organizacion__tipo")
    search_fields = (
        "usuario__username",
        "usuario__email",
        "usuario__first_name",
        "usuario__last_name",
        "organizacion__nombre",
        "organizacion__codigo",
    )
    autocomplete_fields = ("usuario", "organizacion")
    readonly_fields = ("id", "creada_en", "actualizada_en")
    ordering = ("organizacion__nombre", "usuario__username")
