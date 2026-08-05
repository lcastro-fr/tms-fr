from django.contrib.gis.db import models

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
    coordinates = models.PointField(srid=4326, blank=True, null=True, spatial_index=True)
    validada = models.BooleanField(default=True)

    @property
    def latitud(self) -> float | None:
        if self.coordinates:
            return self.coordinates.y
        return None

    @property
    def longitud(self) -> float | None:
        if self.coordinates:
            return self.coordinates.x
        return None

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
