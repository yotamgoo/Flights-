"""Booking.com Flights: read the /api/flights search response the page fetches."""
from __future__ import annotations

from datetime import date

from ..models import Flight, guess_separate, iso_dt, layover_overnight
from .base import Site


def url(d: date) -> str:
    return ("https://flights.booking.com/flights/TLV.AIRPORT-CMB.AIRPORT/?type=ONEWAY&adults=1&cabinClass=ECONOMY"
            f"&from=TLV.AIRPORT&to=CMB.AIRPORT&depart={d.isoformat()}&sort=CHEAPEST")


def capture(u: str) -> bool:
    return "/api/flights" in u


def _price(offer: dict):
    pb = offer.get("priceBreakdown") or {}
    tot = pb.get("total") or pb.get("totalRounded") or {}
    if "units" in tot:
        return tot["units"] + (tot.get("nanos") or 0) / 1e9, tot.get("currencyCode", "USD")
    return None, None


def _flag(obj) -> bool:
    """True if any key mentioning self-transfer / virtual interlining is truthy."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if any(s in kl for s in ("selftransfer", "virtualinterlin", "separateticket")) and v:
                return True
            if isinstance(v, (dict, list)) and _flag(v):
                return True
    elif isinstance(obj, list):
        return any(_flag(x) for x in obj)
    return False


def parse(data: dict, d: date) -> list[Flight]:
    out = []
    for off in (data or {}).get("flightOffers") or []:
        segs = off.get("segments") or []
        if len(segs) != 1:
            continue
        legs = segs[0].get("legs") or []
        if not legs:
            continue
        dep_dt, arr_dt = iso_dt(legs[0]["departureTime"]), iso_dt(legs[-1]["arrivalTime"])
        if dep_dt.date() != d:
            continue
        layovers, overnight = [], False
        for a, b in zip(legs, legs[1:]):
            t1, t2 = iso_dt(a["arrivalTime"]), iso_dt(b["departureTime"])
            layovers.append((a["arrivalAirport"]["code"], int((t2 - t1).total_seconds() // 60)))
            overnight |= layover_overnight(t1, t2)
        names, codes = [], []
        for lg in legs:
            for c in lg.get("carriersData") or []:
                codes.append(c.get("code"))
                if c.get("name") and c["name"] not in names:
                    names.append(c["name"])
        price, cur = _price(off)
        if price is None:
            continue
        tt = segs[0].get("totalTime")
        sep = True if _flag(off) else guess_separate(codes)
        out.append(Flight(
            site="booking", date=d.isoformat(), airlines=names,
            dep=dep_dt.strftime("%H:%M"), arr=arr_dt.strftime("%H:%M"), arr_days=(arr_dt.date() - dep_dt.date()).days,
            duration_min=int(tt // 60) if tt else None, stops=len(legs) - 1, layovers=layovers,
            price=round(price, 2), currency=cur, separate_tickets=sep, overnight=overnight, link=url(d)))
    return out


def extract(page, d: date, captured) -> list[Flight]:
    flights = []
    for _, data in captured:
        flights += parse(data, d)
    return flights


SITE = Site(name="booking", label="Booking.com", url_fn=url, extract=extract, capture=capture,
            ready_selector="[data-testid*='flight_card'], [data-testid*='searchresults_card']", wait_ms=45_000)
