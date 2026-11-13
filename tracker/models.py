"""Flight record and small parsing helpers shared by all extractors."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Low-cost / non-interlining carriers: a connection between two different
# carriers where one of them is in this list is almost always a self-transfer.
LCC_CODES = {"BZ", "G9", "3L", "3O", "E5", "FZ", "W6", "5W", "W4", "FR", "6E", "GQ", "QP", "PC",
             "U2", "IZ", "6H", "J9", "OV", "XY", "VY", "HV", "DY", "D8", "IX", "SG", "TR", "AK"}

AIRLINE_NAMES = {
    "EY": "Etihad", "QR": "Qatar Airways", "A3": "Aegean", "AZ": "ITA Airways", "BZ": "Blue Bird",
    "G9": "Air Arabia", "3L": "Air Arabia Abu Dhabi", "FZ": "flydubai", "EK": "Emirates", "UL": "SriLankan",
    "LY": "El Al", "TK": "Turkish Airlines", "GF": "Gulf Air", "WY": "Oman Air", "SV": "Saudia",
    "AI": "Air India", "6E": "IndiGo", "LX": "SWISS", "WK": "Edelweiss", "LH": "Lufthansa", "BA": "British Airways",
    "MU": "China Eastern", "J2": "AZAL", "GQ": "Sky Express", "W6": "Wizz Air", "5W": "Wizz Air Abu Dhabi",
    "FR": "Ryanair", "PC": "Pegasus", "IZ": "Arkia", "6H": "Israir", "RJ": "Royal Jordanian", "MS": "EgyptAir",
    "ET": "Ethiopian", "LO": "LOT", "KU": "Kuwait Airways", "J9": "Jazeera Airways", "QP": "Akasa Air",
}


@dataclass
class Flight:
    site: str
    date: str                     # departure date YYYY-MM-DD
    airlines: list[str]
    dep: str                      # HH:MM local
    arr: str                      # HH:MM local
    arr_days: int                 # +N days
    duration_min: int | None
    stops: int
    layovers: list[tuple[str, int | None]] = field(default_factory=list)  # (IATA, minutes)
    price: float = 0.0
    currency: str = "USD"
    price_usd: float = 0.0
    separate_tickets: bool | None = None
    overnight: bool | None = None
    link: str = ""

    @property
    def via(self) -> str:
        return "+".join(a for a, _ in self.layovers)

    @property
    def key(self) -> str:
        """Same flight across sites: date + times + connection airports."""
        return f"{self.date}|{self.dep}|{self.arr}+{self.arr_days}|{self.via}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["key"] = self.key
        return d


def hhmm(s: str) -> str:
    """'6:20 AM' / '06:20' / '6:20am' / '12:50a' -> '06:20'."""
    s = s.strip().lower().replace(" ", " ")
    m = re.match(r"(\d{1,2}):(\d{2})\s*([ap])?", s)
    if not m:
        raise ValueError(f"bad time {s!r}")
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}"


def minutes(text: str) -> int | None:
    """'17h 55m', '17 hr 55 min', '9h 50\'', '3 hr', '45 min' -> minutes."""
    if text is None:
        return None
    t = str(text).lower()
    h = re.search(r"(\d+)\s*(?:h|hr|hrs|hour|hours)\b", t)
    m = re.search(r"(\d+)\s*(?:m|min|mins|minutes|')(?![a-z])", t)
    if not h and not m:
        return None
    return (int(h.group(1)) if h else 0) * 60 + (int(m.group(1)) if m else 0)


def money(text) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text))
    return float(m.group(0).replace(",", "")) if m else None


def iso_dt(s: str) -> datetime:
    return datetime.fromisoformat(s[:19])


def layover_overnight(arr_dt: datetime, dep_dt: datetime) -> bool:
    """A layover is 'overnight' if it is long, or spans a chunk of the night."""
    mins = (dep_dt - arr_dt).total_seconds() / 60
    if mins >= 8 * 60:
        return True
    if mins < 3 * 60:
        return False
    # >=3h and covers 01:00-05:00 (local clock at the hub)
    cur = arr_dt
    while cur < dep_dt:
        if 1 <= cur.hour < 5:
            return True
        cur = cur.replace(minute=0, second=0)
        from datetime import timedelta
        cur += timedelta(hours=1)
    return False


def guess_separate(carrier_codes: list[str]) -> bool | None:
    """Heuristic for sites that don't expose a self-transfer flag."""
    codes = [c for c in carrier_codes if c]
    if len(set(codes)) <= 1:
        return False
    for a, b in zip(codes, codes[1:]):
        if a != b and (a in LCC_CODES or b in LCC_CODES):
            return True
    return None
