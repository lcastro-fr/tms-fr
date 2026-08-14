from datetime import date, datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from lib.sap.factory import build_sap_protocol
from tracking.dtos import RemitoUbicacionIn, TicketIngestIn, TicketIngestRemitoIn, TicketIngestOut
from tracking.use_cases import IngestTicketUseCase, ingest_ticket
from lib.routing.factory import build_geocoder
from transportista.dtos import TransportistaIn
from zoneinfo import ZoneInfo
from django.conf import settings

INGEST_TICKET_RFC = "ZZ_RFC_TICKET"
INGEST_TICKET_RFC_DATA_KEY = "ET_DATOS"
PLANTA_CODIGO = "1920"

"""
{'TICKET': 403106, 'VBELN_ENTREGA': 4942517311, 'REMITO': '0102R00009905', 'NRO_INGRESO': 333707,
'FECHA_INGRESO': '2026-07-31', 'HORA_INGRESO': '06:01:00', 'FECHA_EGRESO': '2026-08-02', 'HORA_EGRESO': '21:37:51',
'FECHA_ING_VIG': '2026-07-31', 'HORA_ING_VIG': '05:59:22', 'FECHA_SAL_VIG': '2026-08-03', 'HORA_SAL_VIG': '03:21:03',
'CHAPA': 'AI 186 JL', 'ID_EMPRESA': 'MALDONADO.', 'CUIT': 20254247139, 'FECHA_REMITO': '2026-08-02',
'HORA_REMITO': '19:42:12', 'KUNNR': 500025, 'NAME1': 'CATTER MEAT SOCIEDAD ANONIMA',
'STRAS': 'MARIANA ARBEL 3451', 'ORT01': '9 DE ABRIL  -E. ECHEVERRI', 'REGIO': 1,
'PROVINCIA': 'Buenos Aires', 'LAND1': 'AR', 'TIPO_TRANSP': 'PROPIO'}
"""


class Command(BaseCommand):
    help = "Ingests tickets and remitos into SAP"

    def add_arguments(self, parser):
        parser.add_argument("fecha_desde", type=str, help="Start date for the ingestion process")
        parser.add_argument("fecha_hasta", type=str, help="End date for the ingestion process")

    def handle(self, *args, **options):
        try:
            fecha_desde = datetime.strptime(options["fecha_desde"], "%Y-%m-%d").strftime("%Y%m%d")
            fecha_hasta = datetime.strptime(options["fecha_hasta"], "%Y-%m-%d").strftime("%Y%m%d")
        except ValueError:
            raise CommandError("Invalid date format. Please use YYYY-MM-DD.")

        sap_protocol = build_sap_protocol()

        try:
            sap_response = sap_protocol.call_rfc(
                rfc_name=INGEST_TICKET_RFC,
                params={"FECHA_DESDE": fecha_desde, "FECHA_HASTA": fecha_hasta},
            )
            parsed_response = sap_response.get(INGEST_TICKET_RFC_DATA_KEY, {}).get("value", None)
            if not parsed_response:
                self.stdout.write(
                    self.stdout.write(
                        self.style.SUCCESS(f"Successfully ingested tickets and remitos into SAP")
                    )
                )
                return

        except Exception as e:
            raise CommandError(f"Error calling SAP RFC: {str(e)}")

        try:
            ticket_ingest_in = self._build_ticket_ingest_in(parsed_response)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully built TicketIngestIn DTOs: {ticket_ingest_in}")
            )
        except Exception as e:
            raise CommandError(f"Error building TicketIngestIn DTOs: {str(e)}")

        response : list[TicketIngestOut] = []
        try:
            geocoder = build_geocoder()
            ingest_ticket_use_case = IngestTicketUseCase(geocoder=geocoder)
            for ticket in ticket_ingest_in:
                response.append(ingest_ticket_use_case.execute(ticket))
        except Exception as e:
            raise CommandError(f"Error executing IngestTicketUseCase: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"Successfully ingested tickets and remitos into SAP"))
        for ticket_out in response:
            self.stdout.write(self.style.SUCCESS(f"Ticket {ticket_out.numero} ingested with OS: {ticket_out.orden_servicio_id}"))

    def _build_remito_ubicacion_in(self, remito_data: dict[str, Any]) -> RemitoUbicacionIn:
        return RemitoUbicacionIn(
            codigo=str(remito_data["KUNNR"]),
            nombre=remito_data["NAME1"],
            direccion=remito_data["STRAS"],
            localidad=remito_data["ORT01"],
            provincia=remito_data["PROVINCIA"],
            pais=remito_data["LAND1"],
        )

    def _build_remito_ingest_in(self, remito_data: dict[str, Any]) -> TicketIngestRemitoIn:
        timestamp_remito = self._add_timezone_metadata(datetime.strptime(f"{remito_data['FECHA_REMITO']} {remito_data['HORA_REMITO']}", "%Y-%m-%d %H:%M:%S"))
        return TicketIngestRemitoIn(
            numero=remito_data["REMITO"],
            fecha=timestamp_remito,
            destinos=[self._build_remito_ubicacion_in(remito_data)],
        )

    def _build_transportista_in(self, transp_data: dict[str, Any]) -> TransportistaIn:
        return TransportistaIn(
            cuit=str(transp_data["CUIT"]),
            razon_social=transp_data["ID_EMPRESA"],
        )

    def _add_timezone_metadata(self, date: date | datetime) -> datetime:
        if isinstance(date, datetime):
            return date.astimezone(ZoneInfo(settings.TZ_OPERACION))
        return datetime.combine(date, datetime.min.time()).astimezone(ZoneInfo(settings.TZ_OPERACION))

    def _build_ticket_ingest_in(self, ticket_data: dict[str, Any]) -> list[TicketIngestIn]:
        seen: dict[str, Any] = {}
        for row in ticket_data:
            ticket = str(row.get("TICKET"))
            if not ticket in seen:
                seen[ticket] = {
                    "numero": ticket,
                    "planta_codigo": PLANTA_CODIGO,
                    "fecha_ingreso": self._add_timezone_metadata(datetime.strptime(f"{row['FECHA_ING_VIG']} {row['HORA_ING_VIG']}", "%Y-%m-%d %H:%M:%S")),
                    "fecha_egreso": self._add_timezone_metadata(datetime.strptime(f"{row['FECHA_SAL_VIG']} {row['HORA_SAL_VIG']}", "%Y-%m-%d %H:%M:%S")),
                    "transportista": self._build_transportista_in(row),
                    "tipo_transp": row["TIPO_TRANSP"],
                    "remitos": [],
                }

            seen[ticket]["remitos"].append(self._build_remito_ingest_in(row))

        return [TicketIngestIn(**ticket) for ticket in seen.values()]
