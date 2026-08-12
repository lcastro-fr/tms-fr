from __future__ import annotations

from django.contrib.gis.db.models.functions import GeoFunc
from django.db.models import DecimalField


class SuperficieKm2(GeoFunc):
    """
    Superficie geodésica en km².

    En 4326 el ST_Area de geometry devuelve grados cuadrados, y el Area de Django los
    etiqueta como sq_m igual: el cast a geography es lo que da metros de verdad.
    """

    function = "ST_Area"
    template = "%(function)s(%(expressions)s::geography) / 1000000"
    arity = 1
    output_field = DecimalField(max_digits=12, decimal_places=4)
