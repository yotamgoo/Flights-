"""Sites from the brief that showed a bot check / no results in testing.

They have no extractor: the scraper only loads the page once (in --probe mode)
to see whether they became reachable. See README "Site status".
"""
from __future__ import annotations

from datetime import date

from .base import Site


def _md(d): return d.strftime("%m/%d")
def _ymd(d): return d.isoformat()


TEMPLATES = {
    "kayak": ("Kayak", lambda d: f"https://www.kayak.com/flights/TLV-CMB/{_ymd(d)}?sort=price_a"),
    "momondo": ("Momondo", lambda d: f"https://www.momondo.com/flight-search/TLV-CMB/{_ymd(d)}?sort=price_a"),
    "cheapflights": ("Cheapflights", lambda d: f"https://www.cheapflights.com/flight-search/TLV-CMB/{_ymd(d)}?sort=price_a"),
    "skyscanner": ("Skyscanner", lambda d: f"https://www.skyscanner.net/transport/flights/tlv/cmb/{d.strftime('%y%m%d')}/?adultsv2=1&cabinclass=economy&rtn=0"),
    "kiwi": ("Kiwi.com", lambda d: f"https://www.kiwi.com/en/search/results/tel-aviv-israel/colombo-sri-lanka/{_ymd(d)}/no-return?sortBy=price"),
    "expedia": ("Expedia", lambda d: f"https://www.expedia.com/Flights-Search?trip=oneway&leg1=from:TLV,to:CMB,departure:{_md(d)}/{d.year}TANYT&passengers=adults:1&options=cabinclass:economy&mode=search&sortOrder=INCREASING&sortType=PRICE"),
    "trip": ("Trip.com", lambda d: f"https://www.trip.com/flights/showfarefirst?dcity=tlv&acity=cmb&ddate={_ymd(d)}&triptype=ow&class=y&quantity=1&locale=en-XX&curr=USD"),
    "aviasales": ("Aviasales", lambda d: f"https://www.aviasales.com/search/TLV{d.strftime('%d%m')}CMB1"),
    "skiplagged": ("Skiplagged", lambda d: f"https://skiplagged.com/flights/TLV/CMB/{_ymd(d)}"),
    "cheapoair": ("CheapOair", lambda d: f"https://www.cheapoair.com/air/listing?&d1=TLV&r1=CMB&dt1={_md(d)}/{d.year}&tripType=ONEWAYTRIP&cl=1&ad=1&se=0&ch=0&infl=0&infs=0"),
    "flighthub": ("FlightHub", lambda d: f"https://www.flighthub.com/flight/search?num_adults=1&num_children=0&num_infants=0&num_infants_lap=0&seat_class=Economy&seg0_date={_ymd(d)}&seg0_from=TLV&seg0_to=CMB&type=oneway"),
    "justfly": ("JustFly", lambda d: f"https://www.justfly.com/flight/search?num_adults=1&num_children=0&num_infants=0&num_infants_lap=0&seat_class=Economy&seg0_date={_ymd(d)}&seg0_from=TLV&seg0_to=CMB&type=oneway"),
    "etihad": ("Etihad.com", lambda d: f"https://digital.etihad.com/book/search?LANGUAGE=EN&CHANNEL=DESKTOP&B_LOCATION=TLV&E_LOCATION=CMB&TRIP_TYPE=O&CABIN=E&TRAVELERS=ADT&TRIP_FLOW_TYPE=AVAILABILITY&DATE_1={d.strftime('%Y%m%d')}0000"),
    "issta": ("Issta", lambda d: f"https://www.issta.co.il/flights/results.aspx?route=1&padt=1&pchd=0&pinf=0&pyou=0&dport=tlv&fdate={d.strftime('%d/%m/%Y')}&aport=cmb&dtime=-1&class=y"),
}

SITES = [Site(name=k, label=v[0], url_fn=v[1], wait_ms=20_000) for k, v in TEMPLATES.items()]
