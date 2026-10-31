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


# ── Lote, Stock, Movimiento ──────────────────────────────────────

from apps.inventario.models import Lote, Movimiento, Stock


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ("almacen", "cantidad", "actualizado_en")
    readonly_fields = ("actualizado_en",)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        "insumo", "codigo", "fecha_vencimiento", "proveedor", "creado_en",
    )
    list_filter = ("insumo__categoria",)
    search_fields = ("insumo__nombre", "codigo", "proveedor")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    inlines = [StockInline]


class MovimientoInline(admin.TabularInline):
    model = Movimiento
    extra = 0
    can_delete = False
    fields = (
        "tipo", "cantidad", "cantidad_anterior", "cantidad_nueva",
        "diferencia", "registrado_por", "creado_en",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("almacen", "lote", "cantidad", "actualizado_en")
    list_filter = ("almacen",)
    search_fields = ("almacen__nombre", "lote__codigo", "lote__insumo__nombre")
    readonly_fields = ("id", "actualizado_en")
    inlines = [MovimientoInline]


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        "stock", "tipo", "cantidad", "cantidad_anterior", "cantidad_nueva",
        "registrado_por", "creado_en",
    )
    list_filter = ("tipo",)
    search_fields = ("stock__lote__insumo__nombre", "referencia_id")
    readonly_fields = (
        "id", "stock", "tipo", "cantidad", "cantidad_anterior",
        "cantidad_nueva", "diferencia", "referencia_tipo", "referencia_id",
        "registrado_por", "notas", "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
