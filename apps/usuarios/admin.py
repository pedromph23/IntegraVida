from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name", "telefono")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("Información de contacto", {"fields": ("telefono",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información de contacto", {"fields": ("email", "telefono")}),
    )
