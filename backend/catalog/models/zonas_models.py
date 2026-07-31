from django.contrib.gis.db import models
from shared.models import BaseModel

class Zona(BaseModel):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    geom = models.MultiPolygonField(srid=4326)

    class Meta(BaseModel.Meta):
        db_table = 'zona'
        verbose_name = 'Zona'
        verbose_name_plural = 'Zonas'
