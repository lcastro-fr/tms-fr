from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from catalog.models import Departamento, Pais, Provincia, Ubicacion, Zona


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "active")
    list_filter = ("active",)
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "localidad",
        "provincia",
        "pais",
        "destino_default",
        "active",
    )
    list_filter = ("tipo", "destino_default", "pais", "provincia", "active")
    list_select_related = ("pais",)
    search_fields = ("nombre", "codigo", "localidad")
    autocomplete_fields = ("pais",)
    ordering = ("nombre",)


@admin.register(Zona)
class ZonaAdmin(gis_admin.GISModelAdmin):
    list_display = ("nombre", "active")
    list_filter = ("active",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "superficie_km2", "active")
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "provincia", "superficie_km2", "active")
    list_filter = ("provincia",)
    list_select_related = ("provincia",)
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
