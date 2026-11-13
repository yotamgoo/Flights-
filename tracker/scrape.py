"""Drive headless Chromium: one page at a time, polite delays, no evasion."""
from __future__ import annotations

import os
import random
import time
import traceback
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from . import config
from .models import Flight
from .sites.base import Blocked, Site, check_blocked, load_json


@dataclass
class SiteResult:
    site: Site
    status: str = "not run"       # ok | not reachable | no results | error
    note: str = ""
    flights: list[Flight] = field(default_factory=list)
    dates_ok: list[str] = field(default_factory=list)
    attempts: int = 0


def _log(msg: str) -> None:
    print(msg, flush=True)


def _load(browser, site: Site, d: date, debug_dir: Path | None) -> list[Flight]:
    ctx = browser.new_context(locale=site.locale, viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    captured: list[tuple[str, object]] = []

    def on_response(r):
        if site.capture and site.capture(r.url) and "json" in (r.headers.get("content-type") or ""):
            try:
                data = load_json(r.body())
            except Exception:
                data = None
            if data is not None:
                captured.append((r.url, data))

    page.on("response", on_response)
    try:
        resp = page.goto(site.url(d), wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT_MS)
        status = resp.status if resp else None
        if site.ready_selector:
            try:
                page.wait_for_selector(site.ready_selector, timeout=site.wait_ms)
            except PWTimeout:
                pass
            page.wait_for_timeout(site.settle_ms)
        else:
            page.wait_for_timeout(site.wait_ms)
        try:
            title, body = page.title(), page.inner_text("body", timeout=5000)
        except Exception:
            title, body = "", ""
        flights = site.extract(page, d, captured) if site.extract else []
        if not flights:
            why = check_blocked(status, title, body, page.url)
            if not why and not body.strip():
                why = "blank page (bot protection?)"
            if debug_dir:
                debug_dir.mkdir(parents=True, exist_ok=True)
                stem = f"{site.name}-{d.isoformat()}"
                (debug_dir / f"{stem}.txt").write_text(f"{status} {page.url}\n{title}\n\n{body}")
                try:
                    page.screenshot(path=str(debug_dir / f"{stem}.png"))
                except Exception:
                    pass
            _log(f"    page: HTTP {status} title={title[:60]!r} text={len(body)} chars json={len(captured)}")
            _log("    text: " + " | ".join(l.strip() for l in body.splitlines() if l.strip())[:600])
            if why:
                raise Blocked(why)
        return flights
    finally:
        ctx.close()


def run(sites: list[Site], dates: list[date], debug_dir: Path | None = None) -> list[SiteResult]:
    results = [SiteResult(site=s) for s in sites]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
        first = True
        for res in results:
            s = res.site
            fails = 0
            for d in dates:
                if not first:
                    time.sleep(random.uniform(*config.DELAY_RANGE_S))
                first = False
                res.attempts += 1
                t0 = time.time()
                try:
                    fl = _load(browser, s, d, debug_dir)
                    if not fl:
                        # transient "something went wrong" / slow render: one polite retry
                        time.sleep(random.uniform(*config.DELAY_RANGE_S) + 3)
                        res.attempts += 1
                        fl = _load(browser, s, d, debug_dir)
                    if fl:
                        res.flights += fl
                        res.dates_ok.append(d.isoformat())
                    _log(f"{s.name:12} {d}  {len(fl):3d} flights  ({time.time() - t0:.0f}s)")
                    fails = 0 if fl else fails + 1
                except Blocked as e:
                    _log(f"{s.name:12} {d}  NOT REACHABLE: {e}")
                    res.status, res.note = "not reachable", str(e)
                    break               # captcha/bot wall: don't hammer, move on
                except Exception as e:
                    _log(f"{s.name:12} {d}  ERROR: {e!r}")
                    traceback.print_exc()
                    res.note = f"error: {str(e)[:120]}"
                    fails += 1
                if fails >= 2 and not res.dates_ok:
                    break               # two dates in a row with nothing: give up on this site
            if res.flights:
                res.status = "ok"
                res.note = f"{len(res.dates_ok)}/{len(dates)} dates"
            elif res.status == "not run":
                res.status = "no results" if not res.note.startswith("error") else "error"
        browser.close()
    return results
