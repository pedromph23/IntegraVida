from django.contrib import admin

from apps.auditoria.models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        "ocurrido_en",
        "accion",
        "actor",
        "organizacion_id",
        "tipo_objeto",
        "objeto_id",
        "resultado",
    )

    list_filter = (
        "resultado",
        "accion",
        "ocurrido_en",
    )

    search_fields = (
        "accion",
        "tipo_objeto",
        "objeto_id",
        "id_correlacion",
    )

    date_hierarchy = "ocurrido_en"
    list_select_related = ("actor",)
    list_per_page = 50
    ordering = ("-ocurrido_en",)

    # Todos los campos se presentan como información de solo lectura.
    readonly_fields = tuple(
        campo.name for campo in EventoAuditoria._meta.fields
    )

    def has_add_permission(self, request):
        """Los eventos se crean mediante el servicio de auditoría."""
        return False

    def has_change_permission(self, request, obj=None):
        """No se permite editar eventos históricos desde Django Admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """No se permite eliminar eventos desde Django Admin."""
        return False
