"""Currency conversion, de-duplication across sites, and report categories."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

from . import config
from .models import Flight

SYMBOL = {"USD": "$", "EUR": "€", "ILS": "₪", "GBP": "£"}


def eur_usd() -> float:
    for u in ("https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD",
              "https://api.frankfurter.app/latest?from=EUR&to=USD"):
        try:
            with urllib.request.urlopen(u, timeout=10) as r:
                return float(json.load(r)["rates"]["USD"])
        except Exception:
            continue
    return config.FALLBACK_EUR_USD


def to_usd(flights: list[Flight], rate: float) -> None:
    for f in flights:
        f.price_usd = round(f.price if f.currency == "USD" else f.price * rate if f.currency == "EUR" else f.price, 2)


@dataclass
class Combined:
    key: str
    date: str
    airlines: list[str]
    dep: str
    arr: str
    arr_days: int
    duration_min: int | None
    stops: int
    layovers: list
    separate_tickets: bool | None
    overnight: bool
    prices: dict = field(default_factory=dict)   # site -> Flight (cheapest on that site)
    name_site: str = ""

    @property
    def best(self) -> Flight:
        return min(self.prices.values(), key=lambda f: f.price_usd)

    @property
    def usd(self) -> float:
        return self.best.price_usd

    @property
    def via(self) -> str:
        return "+".join(a for a, _ in self.layovers)

    def is_normal(self) -> bool:
        return (self.stops == 1 and (self.duration_min or 9999) <= config.NORMAL_MAX_MIN
                and not self.overnight and self.separate_tickets is not True)

    def is_reasonable(self) -> bool:
        return self.stops <= 2 and (self.duration_min or 9999) <= config.REASONABLE_MAX_MIN and not self.overnight


PREFERRED_NAMES = ["google", "priceline", "booking", "agoda", "opodo"]


def _fill_unknown_airports(flights: list[Flight]) -> None:
    """Some Google cards hide the connection codes ('?'): borrow them from the same flight elsewhere."""
    known = {}
    for f in flights:
        if f.layovers and all(a != "?" for a, _ in f.layovers):
            known.setdefault((f.date, f.dep, f.arr, f.arr_days, f.stops), f.layovers)
    for f in flights:
        if any(a == "?" for a, _ in f.layovers):
            lay = known.get((f.date, f.dep, f.arr, f.arr_days, f.stops))
            if lay:
                f.layovers = [(a, m if m is not None else lm) for (a, lm), (_, m) in zip(lay, f.layovers)]


def combine(flights: list[Flight]) -> list[Combined]:
    _fill_unknown_airports(flights)
    groups: dict[str, Combined] = {}
    for f in flights:
        c = groups.get(f.key)
        if not c:
            c = groups[f.key] = Combined(key=f.key, date=f.date, airlines=f.airlines, dep=f.dep, arr=f.arr,
                                         arr_days=f.arr_days, duration_min=f.duration_min, stops=f.stops,
                                         layovers=list(f.layovers), separate_tickets=f.separate_tickets,
                                         overnight=bool(f.overnight), name_site=f.site)
        cur = c.prices.get(f.site)
        if cur is None or f.price_usd < cur.price_usd:
            c.prices[f.site] = f
        # merge attributes
        if f.separate_tickets is True:
            c.separate_tickets = True
        elif f.separate_tickets is False and c.separate_tickets is None:
            c.separate_tickets = False
        c.overnight = c.overnight or bool(f.overnight)
        c.duration_min = c.duration_min or f.duration_min
        if any(m is None for _, m in c.layovers) and all(m is not None for _, m in f.layovers):
            c.layovers = list(f.layovers)
        if PREFERRED_NAMES.index(f.site) < PREFERRED_NAMES.index(c.name_site):
            c.airlines, c.name_site = f.airlines, f.site
    return sorted(groups.values(), key=lambda c: c.usd)
