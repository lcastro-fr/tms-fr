from django.contrib import admin

from logistica.models import CostoOrdenServicio, OrdenServicio


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "origen",
        "transportista",
        "tipo_operacion",
        "via",
        "fecha_viaje",
        "tipo_camion",
        "hombreador",
        "active",
    )
    list_filter = ("active", "tipo_operacion", "via", "tipo_camion", "hombreador")
    autocomplete_fields = ("origen", "transportista")
    date_hierarchy = "fecha_viaje"


@admin.register(CostoOrdenServicio)
class CostoOrdenServicioAdmin(admin.ModelAdmin):
    list_display = (
        "orden_servicio",
        "tipo_operacion",
        "precio_flete",
        "dias",
        "precio_dia",
        "total",
        "created_at",
        "active",
    )
    list_filter = ("active", "tipo_operacion", "modalidad")
    readonly_fields = ("total", "subtotal_adicional")
