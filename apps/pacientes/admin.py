from django.contrib import admin

from apps.pacientes.models import ContactoEmergencia, Episodio, Paciente


class ContactoEmergenciaInline(admin.TabularInline):
    model = ContactoEmergencia
    extra = 0
    fields = ("nombre", "parentesco", "telefono", "es_principal")


class EpisodioInline(admin.TabularInline):
    model = Episodio
    extra = 0
    fields = (
        "hospital",
        "refugio",
        "motivo_consulta",
        "estado",
        "fecha_ingreso",
        "fecha_egreso",
    )
    readonly_fields = ("fecha_ingreso",)


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        "apellidos",
        "nombres",
        "cedula",
        "edad",
        "sexo_biologico",
        "creado_en",
    )
    search_fields = (
        "apellidos",
        "nombres",
        "cedula",
        "cedula_hash",
    )
    list_filter = ("sexo_biologico",)
    readonly_fields = ("id", "cedula_hash", "creado_en", "actualizado_en")
    inlines = [ContactoEmergenciaInline, EpisodioInline]

    @admin.display(description="Edad")
    def edad(self, obj):
        return obj.edad or "—"


@admin.register(ContactoEmergencia)
class ContactoEmergenciaAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "nombre",
        "parentesco",
        "telefono",
        "es_principal",
    )
    list_filter = ("parentesco", "es_principal")
    search_fields = ("nombre", "paciente__apellidos")


@admin.register(Episodio)
class EpisodioAdmin(admin.ModelAdmin):
    list_display = (
        "paciente",
        "hospital",
        "refugio",
        "estado",
        "fecha_ingreso",
        "fecha_egreso",
    )
    list_filter = ("estado",)
    search_fields = ("paciente__apellidos", "paciente__nombres")
    readonly_fields = ("id", "creado_en", "actualizado_en")
    date_hierarchy = "fecha_ingreso"
