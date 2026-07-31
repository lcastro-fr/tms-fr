from django.contrib import admin

from catalog.models import Ubicacion


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "tipo", "localidad", "provincia", "active")
    list_filter = ("tipo", "provincia", "active")
    search_fields = ("nombre", "codigo", "localidad")
    ordering = ("nombre",)
