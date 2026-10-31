#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat > apps/derivaciones/admin.py << 'EOF'
from django.contrib import admin

from apps.derivaciones.models import Derivacion, TransicionEstado


class TransicionEstadoInline(admin.TabularInline):
    model = TransicionEstado
    extra = 0
    can_delete = False
    fields = ("estado_anterior", "estado_nuevo", "usuario", "motivo", "creado_en")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Derivacion)
class DerivacionAdmin(admin.ModelAdmin):
    list_display = (
        "episodio",
        "hospital_origen",
        "hospital_destino",
        "prioridad",
        "estado",
        "solicitada_en",
    )
    list_filter = ("estado", "prioridad", "hospital_origen", "hospital_destino")
    search_fields = (
        "episodio__paciente__apellidos",
        "episodio__paciente__nombres",
        "hospital_origen__nombre",
        "hospital_destino__nombre",
    )
    readonly_fields = (
        "id",
        "solicitada_en",
        "aceptada_en",
        "iniciada_en",
        "completada_en",
        "creado_en",
        "actualizado_en",
    )
    inlines = [TransicionEstadoInline]
    date_hierarchy = "solicitada_en"

    def has_add_permission(self, request):
        return False


@admin.register(TransicionEstado)
class TransicionEstadoAdmin(admin.ModelAdmin):
    list_display = (
        "derivacion",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "creado_en",
    )
    list_filter = ("estado_nuevo",)
    search_fields = (
        "derivacion__hospital_origen__nombre",
        "derivacion__hospital_destino__nombre",
    )
    readonly_fields = (
        "id",
        "derivacion",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "motivo",
        "creado_en",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
EOF

echo "OK: Fase 7.3 completada (admin.py)"
