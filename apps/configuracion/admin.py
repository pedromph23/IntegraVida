from django.contrib import admin

from apps.configuracion.models import ReferenciaMigracion


@admin.register(ReferenciaMigracion)
class ReferenciaMigracionAdmin(admin.ModelAdmin):
    list_display = (
        "sistema_origen", "entidad_origen", "identificador_origen",
        "entidad_destino", "resultado_validacion", "creado_en",
    )
    list_filter = ("sistema_origen", "resultado_validacion")
    search_fields = ("entidad_origen", "identificador_origen", "entidad_destino")
    readonly_fields = (
        "id", "sistema_origen", "entidad_origen", "identificador_origen",
        "entidad_destino", "identificador_destino", "hash_origen",
        "resultado_validacion", "detalle_validacion", "migrado_por",
        "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
