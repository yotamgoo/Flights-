"""Agoda Flights: read the flights-bff search API responses the page fetches."""
from __future__ import annotations

import re
from datetime import date

from ..models import Flight, iso_dt, layover_overnight, minutes, money
from .base import Site


def url(d: date) -> str:
    return ("https://www.agoda.com/flights/results?departureFrom=TLV&departureFromType=1&arrivalTo=CMB"
            f"&arrivalToType=1&departDate={d.isoformat()}&searchType=1&cabinType=Economy&adults=1&sort=8")


def capture(u: str) -> bool:
    return "/api/flights-bff/search/v1/flights" in u


def parse(data: dict, d: date) -> list[Flight]:
    items = (((data or {}).get("data") or {}).get("response") or {}).get("content", {}).get("items") or []
    out = []
    for it in items:
        s = it.get("slice") or {}
        segs = s.get("segments") or []
        if not segs or any(x.get("cabinCode") not in (None, "ECO") for x in segs):
            continue
        dep_dt = iso_dt(segs[0]["departure"]["rawDate"])
        arr_dt = iso_dt(segs[-1]["arrival"]["rawDate"])
        if dep_dt.date() != d:
            continue
        layovers, overnight = [], False
        for a, b in zip(segs, segs[1:]):
            t1, t2 = iso_dt(a["arrival"]["rawDate"]), iso_dt(b["departure"]["rawDate"])
            layovers.append((a["arrival"]["airport"]["code"], int((t2 - t1).total_seconds() // 60)))
            overnight |= layover_overnight(t1, t2)
        names = []
        for x in segs:
            n = (x.get("airline") or {}).get("name")
            if n and n not in names:
                names.append(n)
        pr = (it.get("price") or it.get("totalPrice") or {}).get("priceAfterDiscount") or {}
        ac = it.get("analyticsContext") or {}
        price = ac.get("itinerary_price") or money(pr.get("amount"))
        if not price:
            continue
        out.append(Flight(
            site="agoda", date=d.isoformat(), airlines=names,
            dep=dep_dt.strftime("%H:%M"), arr=arr_dt.strftime("%H:%M"), arr_days=(arr_dt.date() - dep_dt.date()).days,
            duration_min=minutes(s.get("duration")), stops=len(segs) - 1, layovers=layovers,
            price=round(float(price), 2), currency=pr.get("currencySymbol") or "USD",
            separate_tickets=bool(ac.get("flights_is_virtual_interline") or ac.get("flight_is_hackerfare")),
            overnight=overnight, link=url(d)))
    return out


def extract(page, d: date, captured) -> list[Flight]:
    # The default sort is "Best"; also ask for the cheapest ones (adds another API response).
    try:
        page.get_by_text(re.compile(r"^Cheapest$")).first.click(timeout=5000)
        page.wait_for_timeout(6000)
    except Exception:
        pass
    flights = []
    for _, data in captured:
        flights += parse(data, d)
    return flights


SITE = Site(name="agoda", label="Agoda", url_fn=url, extract=extract, capture=capture,
            ready_selector="text=/TLV/", wait_ms=40_000, settle_ms=8_000)
