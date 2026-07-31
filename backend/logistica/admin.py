from django.contrib import admin

from logistica.models import OrdenServicio


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ("id", "origen", "transportista", "active")
    list_filter = ("active",)
    autocomplete_fields = ("origen", "transportista")
