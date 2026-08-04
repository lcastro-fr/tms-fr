from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_COL = re.compile(r"[A-Z]+")


def read_rows(path: Path, sheet: str = "xl/worksheets/sheet1.xml") -> list[dict[str, str]]:
    """
    Lee un .xlsx y devuelve las filas de datos como dicts {encabezado: valor}.

    Un .xlsx es un zip de XML, asi que no hace falta openpyxl. Las celdas vacias
    no aparecen en el dict: hay que usar .get() y no indexar.
    """
    with zipfile.ZipFile(path) as z:
        try:
            shared = [
                "".join(t.text or "" for t in si.iter(NS + "t"))
                for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si")
            ]
        except KeyError:
            shared = []
        tree = ET.fromstring(z.read(sheet))

    raw: list[dict[str, str]] = []
    for row in tree.iter(NS + "row"):
        cells: dict[str, str] = {}
        for cell in row.iter(NS + "c"):
            value = cell.find(NS + "v")
            if value is None or value.text is None:
                continue
            text = value.text
            if cell.get("t") == "s":
                text = shared[int(text)]
            text = text.strip()
            if not text:
                continue
            letters = _COL.match(cell.get("r") or "")
            if letters:
                cells[letters.group()] = text
        raw.append(cells)

    if not raw:
        return []

    # Se resuelve por nombre de encabezado y no por letra, para que un export
    # con las columnas reordenadas no corra los campos en silencio.
    header = dict(raw[0].items())
    return [
        {name: cells[letter] for letter, name in header.items() if letter in cells}
        for cells in raw[1:]
    ]
