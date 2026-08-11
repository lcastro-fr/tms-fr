from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from catalog.dtos import UbicacionOpcionOut
from catalog.enums import TipoCamion
from shared.dtos import OpcionOut
from transportista.enums import ModalidadFlete

if TYPE_CHECKING:
    from catalog.models import Zona
    from transportista.models import (
        ConceptoAdicional,
        TarifaConceptoAdicional,
        TarifaFlete,
        Tarifario,
        Transportista,
    )


Precio = Annotated[Decimal, Field(max_digits=14, decimal_places=2, ge=0)]


class TarifaFleteIn(BaseModel):
    zona_id: int | None = None
    ubicacion_id: int | None = None
    modalidad: ModalidadFlete
    tipo_camion: TipoCamion
    hombreador: bool = False
    precio: Precio

    @model_validator(mode="after")
    def _alcance_excluyente(self) -> Self:
        if bool(self.zona_id) == bool(self.ubicacion_id):
            raise ValueError("Elegí una zona o una ubicación, no las dos ni ninguna")
        return self


class TarifaConceptoIn(BaseModel):
    concepto_id: int
    precio: Precio


class TarifarioIn(BaseModel):
    transportista_id: int
    vigente_desde: AwareDatetime
    vigente_hasta: AwareDatetime | None = None
    tarifas_flete: list[TarifaFleteIn] = []
    tarifas_concepto: list[TarifaConceptoIn] = []


class CerrarTarifarioIn(BaseModel):
    vigente_hasta: AwareDatetime


class TarifariosFilters(BaseModel):
    transportista_id: int | None = None
    vencidos: bool | None = None


class TarifaFleteOut(BaseModel):
    id: int
    zona_id: int | None
    zona_nombre: str | None
    ubicacion_id: int | None
    ubicacion_codigo: str | None
    ubicacion_nombre: str | None
    modalidad: str
    tipo_camion: str
    hombreador: bool
    precio: Decimal

    @classmethod
    def from_model(cls, tarifa: TarifaFlete) -> TarifaFleteOut:
        return cls(
            id=tarifa.id,
            zona_id=tarifa.zona_id,
            zona_nombre=tarifa.zona.nombre if tarifa.zona else None,
            ubicacion_id=tarifa.ubicacion_id,
            ubicacion_codigo=tarifa.ubicacion.codigo if tarifa.ubicacion else None,
            ubicacion_nombre=tarifa.ubicacion.nombre if tarifa.ubicacion else None,
            modalidad=tarifa.modalidad,
            tipo_camion=tarifa.tipo_camion,
            hombreador=tarifa.hombreador,
            precio=tarifa.precio,
        )


class TarifaConceptoOut(BaseModel):
    id: int
    concepto_id: int
    concepto_codigo: str
    concepto_nombre: str
    concepto_unidad: str
    precio: Decimal

    @classmethod
    def from_model(cls, tarifa: TarifaConceptoAdicional) -> TarifaConceptoOut:
        return cls(
            id=tarifa.id,
            concepto_id=tarifa.concepto_id,
            concepto_codigo=tarifa.concepto.codigo,
            concepto_nombre=tarifa.concepto.nombre,
            concepto_unidad=tarifa.concepto.unidad,
            precio=tarifa.precio,
        )


class TarifarioOut(BaseModel):
    id: int
    transportista_id: int
    transportista_razon_social: str
    vigente_desde: AwareDatetime
    vigente_hasta: AwareDatetime | None
    cantidad_fletes: int
    cantidad_conceptos: int
    en_uso: bool
    active: bool

    # Devuelve Self y acepta **extra para que la subclase de detalle reuse este mapeo.
    @classmethod
    def from_model(
        cls,
        tarifario: Tarifario,
        en_uso: bool = False,
        cantidad_fletes: int | None = None,
        cantidad_conceptos: int | None = None,
        **extra,
    ) -> Self:
        return cls(
            id=tarifario.id,
            transportista_id=tarifario.transportista_id,
            transportista_razon_social=tarifario.transportista.razon_social,
            vigente_desde=tarifario.vigente_desde,
            vigente_hasta=tarifario.vigente_hasta,
            cantidad_fletes=cantidad_fletes or 0,
            cantidad_conceptos=cantidad_conceptos or 0,
            en_uso=en_uso,
            active=tarifario.active,
            **extra,
        )


class TarifarioDetalleOut(TarifarioOut):
    """El tarifario con sus dos colecciones de tarifas: es lo que carga el formulario."""

    tarifas_flete: list[TarifaFleteOut] = []
    tarifas_concepto: list[TarifaConceptoOut] = []

    @classmethod
    def from_model(
        cls,
        tarifario: Tarifario,
        en_uso: bool = False,
        cantidad_fletes: int | None = None,
        cantidad_conceptos: int | None = None,
        fletes: list[TarifaFlete] | None = None,
        conceptos: list[TarifaConceptoAdicional] | None = None,
        **extra,
    ) -> Self:
        fletes = fletes or []
        conceptos = conceptos or []
        return super().from_model(
            tarifario,
            en_uso,
            cantidad_fletes if cantidad_fletes is not None else len(fletes),
            cantidad_conceptos if cantidad_conceptos is not None else len(conceptos),
            tarifas_flete=[TarifaFleteOut.from_model(f) for f in fletes],
            tarifas_concepto=[TarifaConceptoOut.from_model(c) for c in conceptos],
            **extra,
        )


class TransportistaOpcionOut(BaseModel):
    id: int
    cuit: str
    razon_social: str

    @classmethod
    def from_model(cls, transportista: Transportista) -> TransportistaOpcionOut:
        return cls(
            id=transportista.id,
            cuit=transportista.cuit,
            razon_social=transportista.razon_social,
        )


class ConceptoAdicionalOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    unidad: str
    tipo_operacion: str | None

    @classmethod
    def from_model(cls, concepto: ConceptoAdicional) -> ConceptoAdicionalOut:
        return cls(
            id=concepto.id,
            codigo=concepto.codigo,
            nombre=concepto.nombre,
            unidad=concepto.unidad,
            tipo_operacion=concepto.tipo_operacion,
        )


class ZonaOpcionOut(BaseModel):
    id: int
    nombre: str

    @classmethod
    def from_model(cls, zona: Zona) -> ZonaOpcionOut:
        return cls(id=zona.id, nombre=zona.nombre)


class TarifarioOpcionesOut(BaseModel):
    """
    Todo lo que el formulario necesita para poblar sus <Select>, en un solo request.

    Zonas y ubicaciones viajan acá y no desde /zonas/ y /ubicaciones/ para que editar un
    tarifario no exija además zonas.ver y ubicaciones.ver.
    """

    modalidades: list[OpcionOut]
    tipos_camion: list[OpcionOut]
    transportistas: list[TransportistaOpcionOut]
    conceptos: list[ConceptoAdicionalOut]
    zonas: list[ZonaOpcionOut]
    ubicaciones: list[UbicacionOpcionOut]
