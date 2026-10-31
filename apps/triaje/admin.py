from django.contrib import admin

from apps.triaje.models import Triaje


@admin.register(Triaje)
class TriajeAdmin(admin.ModelAdmin):
    list_display = (
        "episodio",
        "clasificacion",
        "vigente",
        "es_reevaluacion",
        "evaluado_por",
        "evaluado_en",
    )
    list_filter = ("clasificacion", "vigente", "es_reevaluacion")
    search_fields = (
        "episodio__paciente__apellidos",
        "episodio__paciente__nombres",
    )
    readonly_fields = (
        "id",
        "episodio",
        "clasificacion",
        "signos_vitales",
        "observaciones",
        "evaluado_por",
        "evaluado_en",
        "es_reevaluacion",
        "motivo_reevaluacion",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
