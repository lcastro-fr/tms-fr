#!/usr/bin/env python3
"""Convierte Mermas.xlsx a JSON con el schema de TicketIngestIn.

Sólo stdlib: un .xlsx es un zip de XML. No requiere openpyxl ni Django.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Excel cuenta días desde 1900-01-01 pero arrastra el bug del año bisiesto de
# Lotus, y usar 1899-12-30 como epoch lo absorbe.
EXCEL_EPOCH = date(1899, 12, 30)

REPO_ROOT = Path(__file__).resolve().parent.parent

COL_TICKET = "Ticket"
COL_FECHA_INGRESO = "Fecha Ingreso"
COL_HORA_INGRESO = "Hora Ingreso"
COL_FECHA_SALIDA = "Fecha Salida"
COL_HORA_SALIDA = "Hora Salida"
COL_EMPRESA = "Empresaa"
COL_CUIT = "CUIT"
COL_FECHA_REMITO = "Fecha Remito"
COL_HORA_REMITO = "Hora Remito"
COL_REMITO = "Remito"
COL_CUENTA_CLI = "Cuenta Cli."

REQUIRED_COLUMNS = (
    COL_TICKET,
    COL_FECHA_INGRESO,
    COL_HORA_INGRESO,
    COL_FECHA_SALIDA,
    COL_HORA_SALIDA,
    COL_EMPRESA,
    COL_CUIT,
    COL_FECHA_REMITO,
    COL_HORA_REMITO,
    COL_REMITO,
    COL_CUENTA_CLI,
)

# Campos que tienen que ser iguales en todas las filas de un mismo ticket.
TICKET_LEVEL_COLUMNS = (
    COL_FECHA_INGRESO,
    COL_HORA_INGRESO,
    COL_FECHA_SALIDA,
    COL_HORA_SALIDA,
    COL_EMPRESA,
    COL_CUIT,
)


def read_rows(xlsx: Path) -> list[dict[str, str]]:
    """Devuelve las filas de datos como dicts {header: valor}."""
    with zipfile.ZipFile(xlsx) as z:
        shared = [
            "".join(t.text or "" for t in si.iter(NS + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si")
        ]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))

    raw: list[dict[str, str]] = []
    for row in sheet.iter(NS + "row"):
        cells: dict[str, str] = {}
        for cell in row.iter(NS + "c"):
            value = cell.find(NS + "v")
            if value is None or value.text is None:
                continue
            text = value.text
            if cell.get("t") == "s":
                text = shared[int(text)]
            text = text.strip()
            if text:
                letters = re.match(r"[A-Z]+", cell.get("r") or "")
                if letters:
                    cells[letters.group()] = text
        raw.append(cells)

    if not raw:
        raise SystemExit(f"{xlsx}: la hoja está vacía")

    # Resolvemos por nombre de encabezado y no por letra, para que un export con
    # las columnas reordenadas no corra los campos en silencio.
    header = {name: letter for letter, name in raw[0].items()}
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise SystemExit(f"{xlsx}: faltan columnas: {', '.join(missing)}")

    return [
        {name: cells[letter] for name, letter in header.items() if letter in cells}
        for cells in raw[1:]
    ]


def to_datetime(
    serial: str | None, fraction: str | None, tz: timezone
) -> datetime | None:
    if not serial:
        return None
    day = EXCEL_EPOCH + timedelta(days=int(float(serial)))
    # round y no truncado: 0.67081018519820645 * 86400 == 57958.000000...
    seconds = round(float(fraction or 0) * 86400)
    return datetime.combine(day, datetime.min.time(), tz) + timedelta(seconds=seconds)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def parse_offset(text: str) -> timezone:
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", text.strip())
    if not match:
        raise SystemExit(f"--tz-offset inválido: {text!r} (esperado +HH:MM / -HH:MM)")
    sign, hours, minutes = match.groups()
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def build_payloads(
    rows: list[dict[str, str]], planta: str, tz: timezone
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    skipped: list[tuple[str, str, str]] = []

    for row in rows:
        numero = row.get(COL_TICKET)
        if not numero:
            continue
        if not row.get(COL_CUENTA_CLI):
            # destinos exige min_length=1, así que sin Cuenta Cli. no hay remito válido.
            skipped.append((numero, row.get(COL_REMITO, "?"), "sin Cuenta Cli."))
            continue
        grouped.setdefault(numero, []).append(row)

    inconsistent: list[str] = []
    payloads: list[dict[str, Any]] = []
    destinos_vistos: set[str] = set()
    sin_fecha = 0

    for numero, group in grouped.items():
        head = group[0]
        for column in TICKET_LEVEL_COLUMNS:
            if len({r.get(column) for r in group}) > 1:
                inconsistent.append(f"{numero}/{column}")

        remitos = []
        for row in group:
            fecha = to_datetime(row.get(COL_FECHA_REMITO), row.get(COL_HORA_REMITO), tz)
            if fecha is None:
                sin_fecha += 1
            destino = str(int(row[COL_CUENTA_CLI]))
            destinos_vistos.add(destino)
            remitos.append(
                {
                    "numero": row[COL_REMITO],
                    "fecha": iso(fecha),
                    "destinos": [destino],
                }
            )

        payloads.append(
            {
                "numero": numero,
                "planta_codigo": planta,
                "fecha_ingreso": iso(
                    to_datetime(
                        head.get(COL_FECHA_INGRESO), head.get(COL_HORA_INGRESO), tz
                    )
                ),
                "fecha_egreso": iso(
                    to_datetime(
                        head.get(COL_FECHA_SALIDA), head.get(COL_HORA_SALIDA), tz
                    )
                ),
                "transportista": {
                    "cuit": head.get(COL_CUIT, ""),
                    "razon_social": head.get(COL_EMPRESA, ""),
                },
                "remitos": remitos,
            }
        )

    stats = {
        "filas": len(rows),
        "tickets": len(payloads),
        "remitos": sum(len(p["remitos"]) for p in payloads),
        "omitidas": skipped,
        "sin_fecha": sin_fecha,
        "destinos": len(destinos_vistos),
        "inconsistentes": inconsistent,
        "remitos_por_ticket": Counter(len(p["remitos"]) for p in payloads),
    }
    return payloads, stats


def validate(payloads: list[dict[str, Any]]) -> str:
    """Valida contra el DTO real si pydantic está disponible.

    TicketIngestIn sólo importa modelos bajo TYPE_CHECKING, así que se puede
    importar sin configurar Django.
    """
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    try:
        from tracking.dtos import TicketIngestIn
    except ImportError as exc:
        return f"sin validar ({exc.__class__.__name__}: {exc})"

    errors = []
    for payload in payloads:
        try:
            TicketIngestIn.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{payload['numero']}: {exc}")

    if errors:
        for line in errors[:5]:
            print(f"  INVÁLIDO {line}", file=sys.stderr)
        return f"{len(payloads) - len(errors)}/{len(payloads)} válidos"
    return f"{len(payloads)}/{len(payloads)} válidos contra TicketIngestIn"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=REPO_ROOT / "seed/Mermas.xlsx"
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "out/tickets.json")
    parser.add_argument("--planta", default="1920")
    parser.add_argument("--tz-offset", default="-03:00")
    args = parser.parse_args()

    tz = parse_offset(args.tz_offset)
    rows = read_rows(args.input)
    payloads, stats = build_payloads(rows, args.planta, tz)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payloads, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"{args.input.name}: {stats['filas']} filas", file=sys.stderr)
    print(f"  tickets emitidos : {stats['tickets']}", file=sys.stderr)
    print(f"  remitos emitidos : {stats['remitos']}", file=sys.stderr)
    print(f"  remitos sin fecha: {stats['sin_fecha']}", file=sys.stderr)
    print(f"  destinos distintos: {stats['destinos']}", file=sys.stderr)
    print(
        f"  remitos por ticket: {sorted(stats['remitos_por_ticket'].items())}",
        file=sys.stderr,
    )

    if stats["omitidas"]:
        print(f"  filas omitidas   : {len(stats['omitidas'])}", file=sys.stderr)
        for ticket, remito, motivo in stats["omitidas"]:
            print(f"    ticket {ticket} remito {remito}: {motivo}", file=sys.stderr)

    if stats["inconsistentes"]:
        print(
            f"  AVISO campos de ticket inconsistentes: {stats['inconsistentes']}",
            file=sys.stderr,
        )

    print(f"  validación       : {validate(payloads)}", file=sys.stderr)
    print(f"  escrito          : {args.output}", file=sys.stderr)

    print(
        "\nNota: los códigos de destino no existen como Ubicacion todavía, así que "
        "al hacer POST todos los remitos van a salir en remitos_omitidos.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
