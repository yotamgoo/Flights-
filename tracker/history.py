"""Previous run's prices, stored as data/last_run.json and committed by the workflow."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .aggregate import Combined

PATH = Path(__file__).resolve().parent.parent / "data" / "last_run.json"


def load(path: Path = PATH) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def snapshot(combined: list[Combined], label_fn) -> dict:
    per_date: dict[str, float] = {}
    for c in combined:
        per_date[c.date] = min(per_date.get(c.date, 1e9), c.usd)
    return {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "flights": {c.key: {"usd": c.usd, "label": label_fn(c), "date": c.date, "dep": c.dep, "via": c.via,
                            "duration": c.duration_min} for c in combined},
        "per_date": per_date,
        "cheapest": min((c.usd for c in combined), default=None),
    }


def save(snap: dict, path: Path = PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def _match(prev_flights: dict, c: Combined):
    if c.key in prev_flights:
        return prev_flights[c.key]
    # Baseline entries may lack exact times: match on date + connection airports + duration.
    for p in prev_flights.values():
        if (not p.get("dep") and p.get("date") == c.date and p.get("via") == c.via
                and p.get("duration") and c.duration_min and abs(p["duration"] - c.duration_min) <= 10):
            return p
    return None


def changes(prev: dict, combined: list[Combined], tracked: list[Combined]) -> dict:
    """Moves of >= CHANGE_ALERT_USD for tracked flights, per-date minimums and the overall cheapest."""
    t = config.CHANGE_ALERT_USD
    out = {"flights": [], "dates": [], "cheapest": None, "prev_run": prev.get("run_at")}
    pf = prev.get("flights") or {}
    seen = set()
    for c in tracked:
        p = _match(pf, c)
        if p and c.key not in seen:
            seen.add(c.key)
            delta = round(c.usd - p["usd"])
            if abs(delta) >= t:
                out["flights"].append((c, p["usd"], delta))
    now_dates: dict[str, float] = {}
    for c in combined:
        now_dates[c.date] = min(now_dates.get(c.date, 1e9), c.usd)
    for d, v in sorted(now_dates.items()):
        pv = (prev.get("per_date") or {}).get(d)
        if pv is not None and abs(v - pv) >= t:
            out["dates"].append((d, pv, round(v - pv)))
    pc = prev.get("cheapest")
    if pc is not None and combined:
        delta = round(combined[0].usd - pc)
        if abs(delta) >= t:
            out["cheapest"] = (pc, delta)
    return out
