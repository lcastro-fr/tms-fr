from django.contrib.gis.db import models

from catalog.enums import DESTINO_DEFAULT_CHOICES, TIPO_UBICACION_CHOICES, TipoUbicacion
from catalog.models.pais_models import Pais
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
    pais = models.ForeignKey(
        Pais, on_delete=models.PROTECT, related_name="ubicaciones", null=True, blank=True
    )
    coordinates = models.PointField(srid=4326, blank=True, null=True, spatial_index=True)
    validada = models.BooleanField(default=True)
    destino_default = models.CharField(  # noqa: DJ001
        max_length=30, choices=DESTINO_DEFAULT_CHOICES, null=True, blank=True
    )

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
            ),
            models.UniqueConstraint(
                fields=["destino_default"],
                name="uq_ubicacion_destino_default",
                condition=models.Q(destino_default__isnull=False, active=True),
            ),
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
