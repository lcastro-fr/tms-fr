from django.db import models

from catalog.enums import TIPO_UBICACION_CHOICES, TipoUbicacion
from shared.models import BaseModel


class Ubicacion(BaseModel):
    id = models.BigAutoField(primary_key=True)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_UBICACION_CHOICES,
        default=TipoUbicacion.CLIENTE.value,
    )
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=20, blank=True, null=True)
    calle = models.CharField(max_length=200)
    localidad = models.CharField(max_length=120)
    provincia = models.CharField(max_length=120)
    pais = models.CharField(max_length=120, default="Argentina")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "ubicacion"
        verbose_name = "ubicacion"
        verbose_name_plural = "ubicaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="uq_ubicacion_codigo",
                condition=models.Q(codigo__isnull=False, active=True),
            )
        ]
        indexes = [
            models.Index(
                fields=["codigo"],
                name="idx_ubicacion_codigo",
                condition=models.Q(codigo__isnull=False, active=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.codigo})" if self.codigo else self.nombre
