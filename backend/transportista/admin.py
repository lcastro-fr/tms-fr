from django.contrib import admin

from transportista.models import (
    ConceptoAdicional,
    TarifaConceptoAdicional,
    TarifaFlete,
    Tarifario,
    Transportista,
)


@admin.register(Transportista)
class TransportistaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "cuit", "active")
    list_filter = ("active",)
    search_fields = ("razon_social", "cuit")
    ordering = ("razon_social",)


@admin.register(ConceptoAdicional)
class ConceptoAdicionalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "unidad", "tipo_operacion", "active")
    list_filter = ("active", "unidad", "tipo_operacion")
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)


class TarifaFleteInline(admin.TabularInline):
    model = TarifaFlete
    extra = 1
    autocomplete_fields = ("zona", "ubicacion")
    fields = ("zona", "ubicacion", "modalidad", "tipo_camion", "hombreador", "precio", "active")


class TarifaConceptoAdicionalInline(admin.TabularInline):
    model = TarifaConceptoAdicional
    extra = 1
    autocomplete_fields = ("concepto",)
    fields = ("concepto", "precio", "active")


@admin.register(Tarifario)
class TarifarioAdmin(admin.ModelAdmin):
    list_display = ("id", "transportista", "vigente_desde", "vigente_hasta", "active")
    list_filter = ("active",)
    autocomplete_fields = ("transportista",)
    inlines = (TarifaFleteInline, TarifaConceptoAdicionalInline)
    date_hierarchy = "vigente_desde"


@admin.register(TarifaFlete)
class TarifaFleteAdmin(admin.ModelAdmin):
    list_display = (
        "tarifario",
        "zona",
        "ubicacion",
        "modalidad",
        "tipo_camion",
        "hombreador",
        "precio",
        "active",
    )
    list_filter = ("active", "modalidad", "tipo_camion", "hombreador")
    autocomplete_fields = ("zona", "ubicacion")


@admin.register(TarifaConceptoAdicional)
class TarifaConceptoAdicionalAdmin(admin.ModelAdmin):
    list_display = ("tarifario", "concepto", "precio", "active")
    list_filter = ("active", "concepto")
    autocomplete_fields = ("concepto",)
