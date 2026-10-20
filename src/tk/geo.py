"""Ortsauflösung über PLZ_Orte und Haversine-Distanz.

Datenquelle: Blatt ``PLZ_Orte`` (GeoNames über zauberware/postal-codes-json-xml-csv,
CC BY 4.0). Die Logik entspricht Input K bis V (Start) bzw. Q bis V (Ziel) und der
Schnittstelle J2.1 ``resolve_place``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from tk.excelfn import Cell, TextIndex, general_text, is_blank, is_number, to_number, trim
from tk.models import Assumptions
from tk.workbook import WorkbookData

ART_ENTRY = "Eintrag"
ART_ENTRY_UNSURE = "Eintrag unsicher"
ART_PLACE = "Ort"
ART_AMBIGUOUS = "Ort mehrdeutig"
ART_NOT_FOUND = "nicht gefunden"


@dataclass
class PlaceDB:
    """Nachschlagetabellen aus PLZ_Orte (Hauptliste, Ortsverzeichnis, Relationstabelle)."""

    labels: list[object]  # g_Label (A)
    keys: list[object]  # g_Key (B)
    lat: list[object]  # g_Lat (E)
    lon: list[object]  # g_Lon (F)
    qual: list[object]  # g_Qual (I)
    orte: list[object]  # g_Ort (L)
    ort_lat: list[object]  # g_OrtLat (N)
    ort_lon: list[object]  # g_OrtLon (O)
    ort_streu: list[object]  # g_OrtStreu (P)
    rel_keys: list[str]  # g_RelKey (U = TRIM(R)&"|"&TRIM(S))
    rel_km: list[object]  # g_RelKm (T)

    def __post_init__(self) -> None:
        self._label_idx = TextIndex(self.labels)
        self._key_idx = TextIndex(self.keys)
        self._ort_idx = TextIndex(self.orte)
        self._rel_idx = TextIndex(self.rel_keys)

    def match_label(self, text: str) -> int | None:
        return self._label_idx.match(text)

    def match_key(self, text: str) -> int | None:
        return self._key_idx.match(text)

    def match_ort(self, text: str) -> int | None:
        return self._ort_idx.match(text)

    def match_relation(self, text: str) -> int | None:
        return self._rel_idx.match(text)

    def choices(self) -> list[str]:
        """Auswahlliste "PLZ Ort" (l_Auswahl)."""
        return [v for v in self.labels if isinstance(v, str) and v]


def load_place_db(data: WorkbookData) -> PlaceDB:
    rel_cells = data.name_cells("g_RelKey")
    grid = data.sheets[rel_cells[0][0]]
    rel_keys = []
    for _, row, col in rel_cells:
        start, ziel = grid.get((row, col - 3)), grid.get((row, col - 2))
        if is_blank(start) or is_blank(ziel):
            rel_keys.append("")
        else:
            rel_keys.append(trim(general_text(start)) + "|" + trim(general_text(ziel)))
    return PlaceDB(
        labels=data.name_values("g_Label"),
        keys=data.name_values("g_Key"),
        lat=data.name_values("g_Lat"),
        lon=data.name_values("g_Lon"),
        qual=data.name_values("g_Qual"),
        orte=data.name_values("g_Ort"),
        ort_lat=data.name_values("g_OrtLat"),
        ort_lon=data.name_values("g_OrtLon"),
        ort_streu=data.name_values("g_OrtStreu"),
        rel_keys=rel_keys,
        rel_km=data.name_values("g_RelKm"),
    )


@dataclass(slots=True)
class Place:
    """Ergebnis der Ortsauflösung (Input K bis P bzw. Q bis V)."""

    key: str | None  # K / Q
    art: str | None  # L / R
    row: int | None  # M / S, 1-based position in PLZ_Orte list
    label: str | None  # N / T
    lat: float | None  # O / U
    lon: float | None  # P / V


def normalize_key(value: Cell, db: PlaceDB) -> str | None:
    """Input K/Q: PLZ oder Ortsname normiert.

    Zahl 1 bis 99999 wird fünfstellige PLZ; ein Auswahleintrag "PLZ Ort" wird zu seinem
    Schlüssel; Text mit fünf Ziffern am Anfang (allein oder gefolgt von Leerzeichen) wird
    zur PLZ; sonst bleibt der getrimmte Text.
    """
    if is_blank(value):
        return None
    if is_number(value):
        number = to_number(value)
        if 1 <= number <= 99999 and number == int(number):
            return f"{int(number):05d}"
        return trim(general_text(number))
    text = trim(str(value))
    pos = db.match_label(text)
    if pos is not None:
        return general_text(db.keys[pos])
    head = text[:5]
    if len(head) == 5 and head.isascii() and head.isdigit() and (len(text) == 5 or text[5] == " "):
        return head
    return text


def resolve_place(value: Cell, db: PlaceDB, params: Assumptions) -> Place:
    """J2.1 ``resolve_place``: Zuordnung eines Eintrags zu Koordinaten, ohne zu raten.

    Reihenfolge (Assumptions I1.7): PLZ bzw. eigener Schlüssel in der Hauptliste, dann
    Ortsname im Ortsverzeichnis. Ein Ortsname ist nur eindeutig, wenn seine Streuung
    höchstens I02 beträgt; sonst "Ort mehrdeutig". Kein Treffer: "nicht gefunden".
    """
    key = normalize_key(value, db)
    if key is None or key == "":
        return Place(key, None, None, None, None, None)
    pos = db.match_key(key)
    if pos is not None:
        art = ART_ENTRY_UNSURE if db.qual[pos] == "unsicher" else ART_ENTRY
        return Place(key, art, pos + 1, general_text(db.labels[pos]), _num(db.lat[pos]), _num(db.lon[pos]))
    pos = db.match_ort(key)
    if pos is not None:
        streu = db.ort_streu[pos]
        if is_number(streu) and to_number(streu) > params.i02_ort_streuung_km:
            return Place(key, ART_AMBIGUOUS, None, key, None, None)
        label = general_text(db.orte[pos]) + " (Ort)"
        return Place(key, ART_PLACE, pos + 1, label, _num(db.ort_lat[pos]), _num(db.ort_lon[pos]))
    return Place(key, ART_NOT_FOUND, None, key, None, None)


def _num(value: object) -> float | None:
    return to_number(value) if is_number(value) else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> float:
    r"""Luftlinie (Assumptions I2.1, Register K2.1; Input W).

    .. math:: d_L = 2R\arcsin\sqrt{\sin^2\tfrac{\Delta\varphi}{2}
              + \cos\varphi_1\cos\varphi_2\sin^2\tfrac{\Delta\lambda}{2}}

    Annahme: Kugel mit Radius ``I03``; Koordinaten sind PLZ-Schwerpunkte (GeoNames).
    Systemgrenze: Schwerpunkt zu Schwerpunkt, keine Straßengeometrie.
    """
    return (
        2
        * radius_km
        * math.asin(
            math.sqrt(
                math.sin(math.radians(lat2 - lat1) / 2) ** 2
                + math.cos(math.radians(lat1))
                * math.cos(math.radians(lat2))
                * math.sin(math.radians(lon2 - lon1) / 2) ** 2
            )
        )
    )
