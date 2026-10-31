from django.contrib import admin

from apps.inventario.models import Almacen, Insumo


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "nombre", "categoria", "unidad_medida",
        "requiere_lote", "requiere_vencimiento", "activo",
    )
    list_filter = ("categoria", "unidad_medida", "requiere_lote",
                   "requiere_vencimiento", "activo")
    search_fields = ("codigo", "nombre", "subcategoria")
    readonly_fields = ("id", "creado_en", "actualizado_en")


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "nombre", "organizacion", "tipo_ubicacion", "activo",
    )
    list_filter = ("organizacion", "activo")
    search_fields = ("codigo", "nombre", "direccion")
    readonly_fields = ("id", "creado_en", "actualizado_en", "tipo_ubicacion")
