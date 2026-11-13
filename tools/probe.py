import sys, time, pathlib
from playwright.sync_api import sync_playwright
D="2026-11-27"
URLS = {
 "google": "https://www.google.com/travel/flights?q=One%20way%20flights%20from%20TLV%20to%20CMB%20on%202026-11-27&curr=USD&hl=en",
 "kayak": "https://www.kayak.com/flights/TLV-CMB/2026-11-27?sort=price_a",
 "momondo": "https://www.momondo.com/flight-search/TLV-CMB/2026-11-27?sort=price_a",
 "cheapflights": "https://www.cheapflights.com/flight-search/TLV-CMB/2026-11-27?sort=price_a",
 "skyscanner": "https://www.skyscanner.net/transport/flights/tlv/cmb/261127/?adultsv2=1&cabinclass=economy&rtn=0",
 "kiwi": "https://www.kiwi.com/en/search/results/tel-aviv-israel/colombo-sri-lanka/2026-11-27/no-return?sortBy=price",
 "expedia": "https://www.expedia.com/Flights-Search?trip=oneway&leg1=from:TLV,to:CMB,departure:11/27/2026TANYT&passengers=adults:1&options=cabinclass:economy&mode=search&sortOrder=INCREASING&sortType=PRICE",
 "booking": "https://flights.booking.com/flights/TLV.AIRPORT-CMB.AIRPORT/?type=ONEWAY&adults=1&cabinClass=ECONOMY&from=TLV.AIRPORT&to=CMB.AIRPORT&depart=2026-11-27&sort=CHEAPEST",
 "priceline": "https://www.priceline.com/m/fly/search/TLV-CMB-20261127/?cabin-class=ECO&num-adults=1",
 "agoda": "https://www.agoda.com/flights/results?departureFrom=TLV&departureFromType=1&arrivalTo=CMB&arrivalToType=1&departDate=2026-11-27&searchType=1&cabinType=Economy&adults=1&sort=8",
 "trip": "https://www.trip.com/flights/showfarefirst?dcity=tlv&acity=cmb&ddate=2026-11-27&triptype=ow&class=y&quantity=1&locale=en-XX&curr=USD",
 "aviasales": "https://www.aviasales.com/search/TLV2711CMB1",
 "skiplagged": "https://skiplagged.com/flights/TLV/CMB/2026-11-27",
 "opodo": "https://www.opodo.com/travel/#results/type=O;from=TLV;to=CMB;dep=2026-11-27;adults=1;children=0;infants=0;direct=false;internalSearch=true",
 "cheapoair": "https://www.cheapoair.com/air/listing?&d1=TLV&r1=CMB&dt1=11/27/2026&tripType=ONEWAYTRIP&cl=1&ad=1&se=0&ch=0&infl=0&infs=0",
 "flighthub": "https://www.flighthub.com/flight/search?num_adults=1&num_children=0&num_infants=0&num_infants_lap=0&seat_class=Economy&seg0_date=2026-11-27&seg0_from=TLV&seg0_to=CMB&type=oneway",
 "etihad": "https://digital.etihad.com/book/search?LANGUAGE=EN&CHANNEL=DESKTOP&B_LOCATION=TLV&E_LOCATION=CMB&TRIP_TYPE=O&CABIN=E&TRAVELERS=ADT&TRIP_FLOW_TYPE=AVAILABILITY&DATE_1=202611270000",
}
out = pathlib.Path("probe"); out.mkdir(exist_ok=True)
names = sys.argv[1:] or list(URLS)
wait = 25000
with sync_playwright() as p:
    import os
    b = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
    for n in names:
        ctx = b.new_context(locale="en-US", viewport={"width":1366,"height":900})
        pg = ctx.new_page()
        js=[]
        pg.on("response", lambda r, js=js: js.append((r.status, r.headers.get("content-type",""), r.url)))
        t=time.time()
        try:
            r = pg.goto(URLS[n], timeout=60000, wait_until="domcontentloaded")
            st = r.status if r else None
            pg.wait_for_timeout(wait)
            txt = pg.inner_text("body")
            (out/f"{n}.html").write_text(pg.content())
            (out/f"{n}.txt").write_text(txt)
            pg.screenshot(path=str(out/f"{n}.png"))
            print("JSON:", *[f"  {a} {u[:160]}" for a,c,u in js if "json" in c][:40], sep="\n")
            print("TEXT:", txt[:2500].replace("\n"," | "))
            print(f"{n:12} status={st} title={pg.title()[:60]!r} len={len(txt)} url={pg.url[:90]}")
        except Exception as e:
            print(f"{n:12} ERROR {str(e)[:200]}")
        ctx.close()
        time.sleep(3)
    b.close()
