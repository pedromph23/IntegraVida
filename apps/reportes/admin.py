from django.contrib import admin

from apps.reportes.models import RegistroExportacion


@admin.register(RegistroExportacion)
class RegistroExportacionAdmin(admin.ModelAdmin):
    list_display = (
        "contenido", "usuario", "organizacion", "tipo",
        "resultado", "filas_incluidas", "creado_en",
    )
    list_filter = ("contenido", "tipo", "resultado")
    search_fields = ("usuario__username", "detalle")
    readonly_fields = (
        "id", "usuario", "organizacion", "tipo", "contenido",
        "parametros", "filas_incluidas", "archivo_ruta",
        "tamano_bytes", "resultado", "detalle", "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
