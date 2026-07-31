from django.contrib import admin

from tracking.models import Remito, RemitoDestino, Ticket


class RemitoDestinoInline(admin.TabularInline):
    model = RemitoDestino
    extra = 0
    autocomplete_fields = ("ubicacion",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("numero", "planta", "fecha_ingreso", "fecha_egreso", "active")
    list_filter = ("active", "planta")
    search_fields = ("numero",)
    autocomplete_fields = ("planta",)
    date_hierarchy = "fecha_ingreso"


@admin.register(Remito)
class RemitoAdmin(admin.ModelAdmin):
    list_display = ("numero", "fecha", "orden_servicio", "active")
    list_filter = ("active",)
    search_fields = ("numero",)
    inlines = (RemitoDestinoInline,)
