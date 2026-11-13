"""Opodo (eDreams ODIGEO): read the itinerary GraphQL response the page fetches."""
from __future__ import annotations

from datetime import date

from ..models import Flight, guess_separate, iso_dt, layover_overnight
from .base import Site


def url(d: date) -> str:
    return ("https://www.opodo.com/travel/#results/type=O;from=TLV;to=CMB;"
            f"dep={d.isoformat()};adults=1;children=0;infants=0;direct=false;internalSearch=true")


def capture(u: str) -> bool:
    return "itinerary-selection-bff" in u or "frontend-api/service/graphql" in u


def parse(data: dict, d: date, carrier_names: dict | None = None) -> list[Flight]:
    si = (data or {}).get("data", {}).get("searchItinerary")
    if not si:
        return []
    seg = {s["id"]: s["segment"] for s in si.get("segments", [])}
    sec = {s["id"]: s["section"] for s in si.get("sections", [])}
    loc = {l["id"]: l["location"] for l in si.get("locations", [])}
    car = {c["id"]: c["carrier"]["name"] for c in si.get("carriers", [])}
    out = []
    for it in si.get("itineraries", []):
        fees = {f["type"]: f["price"] for f in it.get("fees", [])}
        # Regular (non-member) price; the "discounted" one needs a paid Prime membership.
        p = fees.get("MEMBER_PRICE_POLICY_UNDISCOUNTED") or min(fees.values(), key=lambda x: x["amount"])
        legs = it.get("legs") or []
        if len(legs) != 1:
            continue
        s = seg.get(legs[0]["segmentId"])
        if not s:
            continue
        secs = [sec[x] for x in s["sections"] if x in sec]
        if not secs:
            continue
        first, last = secs[0], secs[-1]
        dep_dt, arr_dt = iso_dt(first["departureDate"]), iso_dt(last["arrivalDate"])
        if dep_dt.date() != d:
            continue
        layovers, overnight = [], False
        for a, b in zip(secs, secs[1:]):
            t1, t2 = iso_dt(a["arrivalDate"]), iso_dt(b["departureDate"])
            layovers.append((loc.get(a["destinationId"], {}).get("iata", "?"), int((t2 - t1).total_seconds() // 60)))
            overnight |= layover_overnight(t1, t2)
        codes = [x.get("carrierId") for x in secs]
        names = []
        for c in codes:
            n = car.get(c, c)
            if n not in names:
                names.append(n)
        out.append(Flight(
            site="opodo", date=d.isoformat(), airlines=names,
            dep=dep_dt.strftime("%H:%M"), arr=arr_dt.strftime("%H:%M"), arr_days=(arr_dt.date() - dep_dt.date()).days,
            duration_min=s.get("duration"), stops=len(secs) - 1, layovers=layovers,
            price=float(p["amount"]), currency=p.get("currency", "EUR"),
            separate_tickets=guess_separate(codes), overnight=overnight, link=url(d)))
    return out


def extract(page, d: date, captured) -> list[Flight]:
    flights = []
    for _, data in captured:
        flights += parse(data, d)
    return flights


SITE = Site(name="opodo", label="Opodo", url_fn=url, extract=extract, capture=capture,
            ready_selector="text=/Select flight/i", wait_ms=40_000)
