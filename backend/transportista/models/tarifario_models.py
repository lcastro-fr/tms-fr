from django.db import models

from catalog.enums import TIPO_CAMION_CHOICES
from catalog.models import Ubicacion, Zona
from shared.models import BaseModel
from transportista.enums import (
    CONCEPTO_UNIDAD_MEDIDA_CHOICES,
    MODALIDAD_FLETE_CHOICES,
    TIPO_OPERACION_CHOICES,
)

from .transportista_models import Transportista


class Tarifario(BaseModel):
    id = models.BigAutoField(primary_key=True)
    transportista = models.ForeignKey(
        Transportista, on_delete=models.PROTECT, related_name="tarifarios"
    )
    vigente_desde = models.DateTimeField()
    vigente_hasta = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "tarifario"
        verbose_name = "Tarifario"
        verbose_name_plural = "Tarifarios"
        ordering = ["-vigente_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["transportista"],
                name="uq_tarifario_transpo_vig",
                condition=models.Q(vigente_hasta=None, active=True),
            )
        ]

    def __str__(self):
        return f"{self.transportista} - {self.vigente_desde.date()} a {self.vigente_hasta.date() if self.vigente_hasta else 'vigente'}"


class TarifaFlete(BaseModel):
    id = models.BigAutoField(primary_key=True)
    tarifario = models.ForeignKey(Tarifario, on_delete=models.CASCADE, related_name="tarifas_flete")

    zona = models.ForeignKey(
        Zona, on_delete=models.PROTECT, related_name="tarifas_flete", null=True, blank=True
    )
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, related_name="tarifas_flete", null=True, blank=True
    )
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_FLETE_CHOICES)
    tipo_camion = models.CharField(max_length=20, choices=TIPO_CAMION_CHOICES)
    hombreador = models.BooleanField(default=False)
    precio = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta(BaseModel.Meta):
        db_table = "tarifa_flete"
        verbose_name = "Tarifa de Flete"
        verbose_name_plural = "Tarifas de Flete"
        ordering = ["modalidad", "tipo_camion"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(zona__isnull=False, ubicacion__isnull=True)
                    | models.Q(zona__isnull=True, ubicacion__isnull=False)
                ),
                name="ck_tarifa_flete_zona_xor_ubicacion",
            ),
            models.UniqueConstraint(
                fields=["tarifario", "zona", "modalidad", "tipo_camion", "hombreador"],
                name="uq_tarifa_flete_zona",
                condition=models.Q(active=True, zona__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["tarifario", "ubicacion", "modalidad", "tipo_camion", "hombreador"],
                name="uq_tarifa_flete_ubicacion",
                condition=models.Q(active=True, ubicacion__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.tarifario} - {self.modalidad} - {self.tipo_camion}"


class ConceptoAdicional(BaseModel):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    unidad = models.CharField(max_length=20, choices=CONCEPTO_UNIDAD_MEDIDA_CHOICES)
    tipo_operacion = models.CharField(  # noqa: DJ001
        max_length=20, choices=TIPO_OPERACION_CHOICES, null=True, blank=True
    )

    class Meta(BaseModel.Meta):
        db_table = "concepto_adicional"
        verbose_name = "Concepto Adicional"
        verbose_name_plural = "Conceptos Adicionales"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="uq_concepto_adicional_codigo",
                condition=models.Q(active=True),
            ),
            models.UniqueConstraint(
                fields=["tipo_operacion"],
                name="uq_concepto_adicional_tipo_operacion",
                condition=models.Q(tipo_operacion__isnull=False, active=True),
            ),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class TarifaConceptoAdicional(BaseModel):
    id = models.BigAutoField(primary_key=True)
    tarifario = models.ForeignKey(
        Tarifario, on_delete=models.CASCADE, related_name="tarifas_conceptos"
    )
    concepto = models.ForeignKey(
        ConceptoAdicional, on_delete=models.PROTECT, related_name="tarifas_conceptos"
    )

    precio = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta(BaseModel.Meta):
        db_table = "tarifa_concepto_adicional"
        verbose_name = "Tarifa de Concepto Adicional"
        verbose_name_plural = "Tarifas de Conceptos Adicionales"
        constraints = [
            models.UniqueConstraint(
                fields=["tarifario", "concepto"],
                name="uq_tarifa_concepto",
                condition=models.Q(active=True),
            )
        ]

    def __str__(self):
        return f"{self.tarifario} - {self.concepto}"
