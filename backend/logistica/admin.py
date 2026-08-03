from django.contrib import admin

from logistica.models import OrdenServicio


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ("id", "origen", "transportista", "tipo_camion", "hombreador", "active")
    list_filter = ("active", "tipo_camion", "hombreador")
    autocomplete_fields = ("origen", "transportista")
