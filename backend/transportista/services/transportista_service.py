from __future__ import annotations

from transportista.models import Transportista


class TransportistaService:
    model = Transportista

    @staticmethod
    def create_transportista(cuit: str, razon_social: str) -> Transportista:
        return Transportista.objects.create(cuit=cuit, razon_social=razon_social)

    @staticmethod
    def get_transportista(**filters) -> Transportista | None:
        return Transportista.objects.filter(**filters).first()

    @staticmethod
    def get_or_create(cuit: str, razon_social: str) -> Transportista:
        transportista = TransportistaService.get_transportista(cuit=cuit)
        if transportista is None:
            transportista = TransportistaService.create_transportista(
                cuit=cuit, razon_social=razon_social
            )
        return transportista
