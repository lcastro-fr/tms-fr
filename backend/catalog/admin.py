from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from catalog.models import Ubicacion, Zona


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "tipo", "localidad", "provincia", "active")
    list_filter = ("tipo", "provincia", "active")
    search_fields = ("nombre", "codigo", "localidad")
    ordering = ("nombre",)


@admin.register(Zona)
class ZonaAdmin(gis_admin.GISModelAdmin):
    list_display = ("nombre", "active")
    list_filter = ("active",)
    search_fields = ("nombre",)
    ordering = ("nombre",)
