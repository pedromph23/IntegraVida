from django.contrib import admin

from apps.refugios.models import Necesidad, Refugio, RegistroOcupacion


class NecesidadInline(admin.TabularInline):
    model = Necesidad
    extra = 0
    fields = (
        "categoria",
        "descripcion",
        "prioridad",
        "cantidad_estimada",
        "cubierta",
    )


class RegistroOcupacionInline(admin.TabularInline):
    model = RegistroOcupacion
    extra = 0
    can_delete = False
    fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "notas",
        "registrado_por",
        "creado_en",
    )
    readonly_fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Refugio)
class RefugioAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "organizacion",
        "estado_operativo",
        "ocupacion_actual",
        "capacidad_total",
        "porcentaje_ocupacion_display",
    )
    list_filter = ("tipo", "estado_operativo", "organizacion")
    search_fields = ("nombre", "codigo", "direccion")
    readonly_fields = (
        "id",
        "creado_en",
        "actualizado_en",
        "capacidad_disponible_display",
        "porcentaje_ocupacion_display",
    )
    inlines = [NecesidadInline, RegistroOcupacionInline]

    @admin.display(description="% ocupación")
    def porcentaje_ocupacion_display(self, obj):
        return f"{obj.porcentaje_ocupacion}%"

    @admin.display(description="Capacidad disponible")
    def capacidad_disponible_display(self, obj):
        return obj.capacidad_disponible


@admin.register(Necesidad)
class NecesidadAdmin(admin.ModelAdmin):
    list_display = (
        "refugio",
        "categoria",
        "prioridad",
        "cubierta",
        "creada_en",
    )
    list_filter = ("categoria", "prioridad", "cubierta")
    search_fields = ("descripcion", "refugio__nombre")
    readonly_fields = ("id", "creada_en", "actualizada_en")


@admin.register(RegistroOcupacion)
class RegistroOcupacionAdmin(admin.ModelAdmin):
    list_display = (
        "refugio",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "creado_en",
    )
    list_filter = ("fuente",)
    search_fields = ("refugio__nombre",)
    readonly_fields = (
        "id",
        "refugio",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "fuente",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
