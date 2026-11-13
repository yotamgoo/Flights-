"""Priceline: results are server-rendered into window.__PRELOADED_STATE__."""
from __future__ import annotations

from datetime import date

from ..models import Flight, iso_dt, layover_overnight
from .base import Site


def url(d: date) -> str:
    return f"https://www.priceline.com/m/fly/search/TLV-CMB-{d.strftime('%Y%m%d')}/?cabin-class=ECO&num-adults=1"


def parse(state: dict, d: date) -> list[Flight]:
    out = []
    for it in ((state or {}).get("listings") or {}).get("response") or []:
        sl = (it.get("slices") or [None])[0]
        if not sl:
            continue
        segs = sl.get("segments") or []
        dep_dt = iso_dt(sl["departInfo"]["time"]["dateTime"])
        arr_dt = iso_dt(sl["arrivalInfo"]["time"]["dateTime"])
        if dep_dt.date() != d:
            continue
        layovers, overnight = [], False
        for a, b in zip(segs, segs[1:]):
            t1, t2 = iso_dt(a["arrivalInfo"]["time"]["dateTime"]), iso_dt(b["departInfo"]["time"]["dateTime"])
            layovers.append((a["arrivalInfo"]["airport"]["code"], int((t2 - t1).total_seconds() // 60)))
            overnight |= layover_overnight(t1, t2)
        price = next((p["amount"] for p in it.get("price", []) if p.get("type") == "TOTAL_PRICE"), None)
        cur = next((p.get("currencyCode") for p in it.get("price", []) if p.get("currencyCode")), "USD")
        if price is None:
            continue
        out.append(Flight(
            site="priceline", date=d.isoformat(), airlines=[a["name"] for a in it.get("airlines", [])],
            dep=dep_dt.strftime("%H:%M"), arr=arr_dt.strftime("%H:%M"), arr_days=(arr_dt.date() - dep_dt.date()).days,
            duration_min=int(sl.get("durationInMinutes") or 0) or None, stops=int(sl.get("stops") or 0),
            layovers=layovers, price=float(price), currency=cur,
            separate_tickets=bool(it.get("isFused")), overnight=overnight or bool(sl.get("isOvernight")),
            link=url(d)))
    return out


def extract(page, d: date, captured) -> list[Flight]:
    state = page.evaluate("() => window.__PRELOADED_STATE__ || null")
    return parse(state, d)


SITE = Site(name="priceline", label="Priceline", url_fn=url, extract=extract,
            ready_selector="text=/Stops?/", wait_ms=30_000)
