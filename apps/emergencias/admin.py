from django.contrib import admin

from apps.emergencias.models import Emergencia, ReporteEmergencia


@admin.register(Emergencia)
class EmergenciaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "categoria",
        "gravedad",
        "estado",
        "municipio",
        "creada_en",
    )
    list_filter = ("categoria", "gravedad", "estado")
    search_fields = ("titulo", "descripcion", "ubicacion_texto")
    readonly_fields = ("id", "estado", "creada_en", "actualizada_en")
    date_hierarchy = "creada_en"


@admin.register(ReporteEmergencia)
class ReporteEmergenciaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "emergencia",
        "canal",
        "estado_revision",
        "recibido_en",
    )
    list_filter = ("canal", "estado_revision")
    search_fields = ("descripcion", "ubicacion_texto")
    readonly_fields = ("id", "emergencia", "estado_revision", "recibido_en")
    date_hierarchy = "recibido_en"