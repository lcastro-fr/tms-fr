from __future__ import annotations

from catalog.enums import DestinoDefault
from transportista.enums import Via

DESTINO_DEFAULT_POR_VIA = {
    Via.MARITIMA: DestinoDefault.PUERTO_MARITIMO,
    Via.AEREA: DestinoDefault.AEROPUERTO,
}
