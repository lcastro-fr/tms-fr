from django.contrib import admin

from transportista.models import Transportista


@admin.register(Transportista)
class TransportistaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "cuit", "active")
    list_filter = ("active",)
    search_fields = ("razon_social", "cuit")
    ordering = ("razon_social",)
