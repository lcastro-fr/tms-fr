from django.db import models
from django.db.models import Q

from shared.models import BaseModel


class Transportista(BaseModel):
    id = models.BigAutoField(primary_key=True)
    cuit = models.CharField(max_length=13)
    razon_social = models.CharField(max_length=200)

    class Meta(BaseModel.Meta):
        db_table = "transportista"
        verbose_name = "transportista"
        verbose_name_plural = "transportistas"
        constraints = [
            models.UniqueConstraint(
                fields=["cuit"],
                condition=Q(active=True),
                name="uq_carrier_active_cuit",
            )
        ]

    def __str__(self) -> str:
        return f"{self.razon_social} ({self.cuit})"
