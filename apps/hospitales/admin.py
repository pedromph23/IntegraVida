from django.contrib import admin

from apps.hospitales.models import (
    Hospital,
    HospitalServicio,
    RecursoHospitalario,
    RegistroDisponibilidad,
    Servicio,
)


class HospitalServicioInline(admin.TabularInline):
    model = HospitalServicio
    extra = 0
    autocomplete_fields = ("servicio",)
    fields = ("servicio", "disponible", "notas", "actualizado_en")
    readonly_fields = ("actualizado_en",)


class RecursoHospitalarioInline(admin.TabularInline):
    model = RecursoHospitalario
    extra = 0
    fields = ("tipo", "capacidad_total", "disponible", "actualizado_en")
    readonly_fields = ("actualizado_en",)


class RegistroDisponibilidadInline(admin.TabularInline):
    model = RegistroDisponibilidad
    extra = 0
    can_delete = False
    fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "notas",
        "registrado_por",
        "creado_en",
    )
    readonly_fields = (
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "notas",
        "registrado_por",
        "creado_en",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "nivel",
        "estado_operativo",
        "organizacion",
    )
    list_filter = ("tipo", "nivel", "estado_operativo", "organizacion")
    search_fields = ("nombre", "codigo", "direccion")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    inlines = [HospitalServicioInline, RecursoHospitalarioInline]


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "tipo", "activo")
    list_filter = ("tipo", "activo")
    search_fields = ("nombre", "codigo")
    readonly_fields = ("id",)


@admin.register(RecursoHospitalario)
class RecursoHospitalarioAdmin(admin.ModelAdmin):
    list_display = (
        "hospital",
        "tipo",
        "capacidad_total",
        "disponible",
        "ocupados",
        "actualizado_en",
    )
    list_filter = ("tipo",)
    search_fields = ("hospital__nombre", "hospital__codigo")
    readonly_fields = ("id", "actualizado_en", "ocupados")
    inlines = [RegistroDisponibilidadInline]


@admin.register(RegistroDisponibilidad)
class RegistroDisponibilidadAdmin(admin.ModelAdmin):
    list_display = (
        "recurso",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
        "registrado_por",
        "creado_en",
    )
    search_fields = ("recurso__hospital__nombre",)
    readonly_fields = (
        "id",
        "recurso",
        "cantidad_anterior",
        "cantidad_nueva",
        "diferencia",
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
