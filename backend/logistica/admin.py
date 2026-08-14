from django.contrib import admin

from logistica.models import CostoOrdenServicio, OrdenServicio, OrdenServicioDestino


class OrdenServicioDestinoInline(admin.TabularInline):
    model = OrdenServicioDestino
    extra = 0
    fields = ("ubicacion", "secuencia", "active")
    autocomplete_fields = ("ubicacion",)


@admin.register(OrdenServicioDestino)
class OrdenServicioDestinoAdmin(admin.ModelAdmin):
    list_display = ("orden_servicio", "ubicacion", "secuencia", "active")
    list_filter = ("active",)
    autocomplete_fields = ("orden_servicio", "ubicacion")


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    inlines = (OrdenServicioDestinoInline,)
    search_fields = ("=id",)
    list_display = (
        "id",
        "origen",
        "transportista",
        "tipo_operacion",
        "via",
        "fecha_viaje",
        "tipo_camion",
        "hombreador",
        "facturable",
        "costo_real",
        "active",
    )
    list_filter = ("active", "tipo_operacion", "via", "tipo_camion", "hombreador", "facturable")
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
