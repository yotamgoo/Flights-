"""Google Flights: parse the result cards (visible text + aria-label)."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import quote

from ..models import Flight, hhmm, minutes, money
from .base import Site


def url(d: date) -> str:
    q = quote(f"One way flights from TLV to CMB on {d.isoformat()}")
    return f"https://www.google.com/travel/flights?q={q}&curr=USD&hl=en"


TIME = r"\d{1,2}:\d{2}\s?[AP]M"
MAIN = re.compile(
    r"From ([\d,]+) US dollars\. (Nonstop|\d+ stops?) flight with (.+?)\.\s+"
    rf"(?:.*?)Leaves .+? at ({TIME}) on \w+, (\w+ \d+) and arrives at .+? at ({TIME}) on \w+, (\w+ \d+)\.\s+"
    r"Total duration ([\d hrmin]+)\.", re.S)


def _md(s: str, year: int) -> date:
    return datetime.strptime(f"{s} {year}", "%B %d %Y").date()


def parse_card(text: str, aria: str, d: date, link: str) -> Flight | None:
    """aria: the card's main label ("From 606 US dollars. 2 stops flight with ...")."""
    aria = aria.replace("\u202f", " ").replace("\xa0", " ")
    m = MAIN.search(aria)
    if not m:
        return None
    price = money(m.group(1))
    stops = 0 if m.group(2) == "Nonstop" else int(m.group(2).split()[0])
    airlines = [a.strip() for a in re.split(r",\s*|\s+and\s+", m.group(3)) if a.strip()]
    dep_d, arr_d = _md(m.group(5), d.year), _md(m.group(7), d.year)
    if dep_d != d:
        return None
    lay_mins = [minutes(x) for x in re.findall(r"is a ([\d hrmin]+?) (?:overnight )?layover", aria)]

    # connection airport codes come from the visible text: "3 hr AUH" or "ATH, DOH"
    codes: list[str] = []
    lines = [l.strip() for l in text.replace("\u202f", " ").replace("\xa0", " ").splitlines() if l.strip()]
    if stops:
        for l in lines:
            mm = re.fullmatch(r"(?:[\d hrmin]+ )?([A-Z]{3}(?:, [A-Z]{3})*)", l)
            if mm and "TLV" not in l and "CMB" not in l:
                codes = mm.group(1).split(", ")
                break
    n = max(stops, len(codes))
    layovers = [(codes[i] if i < len(codes) else "?", lay_mins[i] if i < len(lay_mins) else None) for i in range(n)]

    low = (text + " " + aria).lower()
    separate = any(k in low for k in ("separate ticket", "self transfer", "self-transfer"))
    overnight = "overnight" in low or any((x or 0) >= 8 * 60 for _, x in layovers)
    return Flight(site="google", date=d.isoformat(), airlines=airlines, dep=hhmm(m.group(4)), arr=hhmm(m.group(6)),
                  arr_days=(arr_d - dep_d).days, duration_min=minutes(m.group(8)), stops=stops, layovers=layovers,
                  price=price, currency="USD", separate_tickets=separate, overnight=overnight, link=link)


def extract(page, d: date, captured) -> list[Flight]:
    # expand "View more flights" once if present
    try:
        more = page.get_by_role("button", name=re.compile(r"more flights", re.I))
        if more.count():
            more.first.click(timeout=5000)
            page.wait_for_timeout(3000)
    except Exception:
        pass
    best: dict[str, Flight] = {}
    # innermost <li> rows only (outer containers also contain the aria-labelled element)
    cards = page.locator("li:not(:has(li))").filter(has=page.locator('[aria-label*="Select flight"], [aria-label^="From "]'))
    for i in range(cards.count()):
        c = cards.nth(i)
        try:
            text = c.inner_text(timeout=3000)
            labels = c.locator("[aria-label]").evaluate_all("els => els.map(e => e.getAttribute('aria-label'))")
            aria = next((a for a in labels if a and a.startswith("From ")), "")
        except Exception:
            continue
        f = parse_card(text, aria, d, url(d))
        if f and (f.key not in best or f.price < best[f.key].price):
            best[f.key] = f
    return list(best.values())


SITE = Site(name="google", label="Google Flights", url_fn=url, extract=extract,
            ready_selector='li [aria-label*="Select flight"], li [aria-label^="From "]', wait_ms=35_000)
