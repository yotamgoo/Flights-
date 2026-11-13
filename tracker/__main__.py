"""CLI.

  python -m tracker run     [--sites google,opodo] [--dates 2026-11-27] [--no-send] [--no-save]
  python -m tracker probe   [--sites ...] [--date 2026-11-27]   # reachability table for every site
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import aggregate, config, history, report, scrape, telegram
from .sites import ACTIVE, ALL, BY_NAME, PROBE_ONLY

ROOT = Path(__file__).resolve().parent.parent


def _sites(arg: str | None, default):
    return [BY_NAME[n.strip()] for n in arg.split(",")] if arg else default


def cmd_run(a) -> int:
    today = datetime.now(timezone.utc).date()
    if today > config.STOP_AFTER and not a.force:
        print(f"Trip window is over ({today} > {config.STOP_AFTER}); nothing to do.")
        return 0
    dates = [date.fromisoformat(x) for x in a.dates.split(",")] if a.dates else config.DATES
    sites = _sites(a.sites, ACTIVE)
    results = scrape.run(sites, dates, debug_dir=ROOT / "debug")
    flights = [f for r in results for f in r.flights]
    rate = aggregate.eur_usd()
    aggregate.to_usd(flights, rate)
    combined = aggregate.combine(flights)
    tracked = [c for c in combined if c.is_reasonable()] + combined[:1]
    prev = history.load()
    chg = history.changes(prev, combined, tracked)
    inactive = [s.label for s in PROBE_ONLY]
    html = report.build(combined, results, chg, inactive)

    (ROOT / "report.md").write_text(report.to_markdown(html))
    (ROOT / "results.json").write_text(json.dumps(
        {"eur_usd": rate, "sites": {r.site.name: {"status": r.status, "note": r.note, "dates_ok": r.dates_ok}
                                    for r in results},
         "flights": [f.to_dict() for f in flights]}, indent=1, ensure_ascii=False))
    print("\n" + report.to_markdown(html))
    if combined and not a.no_save:
        history.save(history.snapshot(combined, report.label))
    if not a.no_send:
        telegram.send(html)
    return 0


def cmd_probe(a) -> int:
    d = date.fromisoformat(a.date)
    sites = _sites(a.sites, ALL)
    results = scrape.run(sites, [d], debug_dir=ROOT / "debug")
    flights = [f for r in results for f in r.flights]
    aggregate.to_usd(flights, aggregate.eur_usd())
    rows = ["| Site | Status | Flights | Cheapest | Note |", "|---|---|---|---|---|"]
    for r in results:
        cheap = min(r.flights, key=lambda f: f.price_usd) if r.flights else None
        c = f"{cheap.currency} {cheap.price:,.0f} {'+'.join(cheap.airlines)} {cheap.dep}" if cheap else ""
        rows.append(f"| {r.site.label} | {r.status} | {len(r.flights)} | {c} | {r.note} |")
    table = "\n".join(rows)
    print("\n" + table)
    (ROOT / "probe.md").write_text(f"# Site probe {d}\n\n{table}\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tracker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sites")
    r.add_argument("--dates")
    r.add_argument("--no-send", action="store_true")
    r.add_argument("--no-save", action="store_true")
    r.add_argument("--force", action="store_true", help="run even after the trip window")
    p = sub.add_parser("probe")
    p.add_argument("--sites")
    p.add_argument("--date", default="2026-11-27")
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else cmd_probe(a)


if __name__ == "__main__":
    sys.exit(main())
