"""Hebrew, phone-friendly report (Telegram HTML + Markdown copy)."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from html import escape

from . import config
from .aggregate import SYMBOL, Combined
from .scrape import SiteResult

HEB_DOW = ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"]  # Monday..Sunday
SHORT = {"google": "Google", "opodo": "Opodo", "agoda": "Agoda", "booking": "Booking", "priceline": "Priceline"}


def d_he(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day}/{d.month} {HEB_DOW[d.weekday()]}"


def dur(m: int | None) -> str:
    return "?" if not m else f"{m // 60}h{m % 60:02d}"


def usd(v: float) -> str:
    return f"${v:,.0f}"


def native(f) -> str:
    s = SYMBOL.get(f.currency, f.currency + " ")
    txt = f"{s}{f.price:,.0f}"
    if f.currency != "USD":
        txt += f" (~{usd(f.price_usd)})"
    return txt


def airlines(c: Combined) -> str:
    names = []
    for a in c.airlines:
        m = re.search(r"\(([^)]+)\)", a)          # "Italia Trasporto Aereo (ITA Airways)" -> "ITA Airways"
        a = m.group(1) if m else a
        names.append(re.sub(r"\s+(Airways|Airlines|Air Lines|Airline)$", "", a).strip())
    names = names or ["?"]
    return escape(" + ".join(dict.fromkeys(names)))


def times(c: Combined) -> str:
    plus = f"+{c.arr_days}" if c.arr_days else ""
    return f"{c.dep}→{c.arr}{plus}"


def layovers(c: Combined) -> str:
    if not c.layovers:
        return "ישירה"
    parts = [f"{a} ({dur(m)})" if m else a for a, m in c.layovers]
    return "עצירה ב-" + ", ".join(parts)


def tickets(c: Combined) -> str:
    return {True: "⚠️ כרטיסים נפרדים", False: "כרטיס אחד", None: "כרטיס: לא ידוע"}[c.separate_tickets]


def site_prices(c: Combined) -> str:
    items = sorted(c.prices.items(), key=lambda kv: kv[1].price_usd)
    return " · ".join(f"{SHORT.get(s, s)} {native(f)}" for s, f in items)


def link(c: Combined, text: str | None = None) -> str:
    b = c.best
    return f'<a href="{escape(b.link, quote=True)}">{escape(text or "לזול ביותר: " + SHORT.get(b.site, b.site))}</a>'


def label(c: Combined) -> str:
    """Plain one-liner used in history + change lines."""
    return f"{d_he(c.date)} {re.sub('<[^>]+>', '', airlines(c))} {times(c)}"


def flight_block(i: int, c: Combined, show_tickets: bool) -> str:
    l1 = f"{i}. <b>{usd(c.usd)}</b> · {d_he(c.date)} · {airlines(c)}"
    l2 = f"{times(c)} · {dur(c.duration_min)} · {escape(layovers(c))}"
    if show_tickets:
        l2 += f" · {tickets(c)}"
    l3 = f"{escape(site_prices(c))} · {link(c)}"
    return "\n".join([l1, l2, l3])


def build(combined: list[Combined], results: list[SiteResult], chg: dict, inactive: list[str]) -> str:
    normal = [c for c in combined if c.is_normal()][:5]
    normal_keys = {c.key for c in normal}
    reasonable = [c for c in combined if c.is_reasonable() and c.key not in normal_keys][:4]
    cheapest = combined[0] if combined else None
    now = datetime.now(ZoneInfo("Asia/Jerusalem"))
    out = [f"✈️ <b>TLV → CMB · דו״ח מחירים {now.day}/{now.month}</b>\n(כיוון אחד, מבוגר 1, תיירים, 25/11–1/12)"]

    # 1. recommendation
    if normal:
        b = normal[0]
        rec = f"💡 <b>המלצה היום:</b> {airlines(b)} {d_he(b.date)} {times(b)} ב-<b>{usd(b.usd)}</b> ב-{SHORT.get(b.best.site)}"
        moved = next((d for c, _, d in chg["flights"] if c.key == b.key), None)
        if moved:
            rec += f" ({'ירד' if moved < 0 else 'עלה'} ${abs(moved)} מאתמול)"
        if reasonable and reasonable[0].usd < b.usd - 80:
            rec += f"; לחיסכון: {usd(reasonable[0].usd)} בטיסה ארוכה יותר"
    elif reasonable:
        b = reasonable[0]
        rec = f"💡 <b>המלצה היום:</b> אין טיסה נורמלית; הכי סבירה {airlines(b)} {d_he(b.date)} ב-<b>{usd(b.usd)}</b>"
    else:
        rec = "💡 <b>המלצה היום:</b> לא נמצאו טיסות היום – בדקו שוב מחר"
    out.append(rec)

    # 2. normal
    sec = ["🟢 <b>טיסות נורמליות</b> (עצירה 1, עד ~12 שע׳, בלי לילה)"]
    sec += [flight_block(i, c, False) for i, c in enumerate(normal, 1)] or ["לא נמצאו היום."]
    out.append("\n\n".join(sec))

    # 3. cheap but reasonable
    sec = ["🟡 <b>זולות אבל סבירות</b> (עד 2 עצירות, עד ~20 שע׳, בלי לילה)"]
    sec += [flight_block(i, c, True) for i, c in enumerate(reasonable, 1)] or ["לא נמצאו היום."]
    out.append("\n\n".join(sec))

    # 4. absolute cheapest
    if cheapest:
        out.append(f"💸 <b>הכי זול שיש:</b> {usd(cheapest.usd)} · {d_he(cheapest.date)} · {airlines(cheapest)} · "
                   f"{times(cheapest)} · {dur(cheapest.duration_min)} · {escape(layovers(cheapest))} · "
                   f"{tickets(cheapest)}{' · לילה בעצירה' if cheapest.overnight else ''} · {link(cheapest, SHORT.get(cheapest.best.site))}")

    # 5. per date
    lines = ["📅 <b>הכי זול לפי תאריך</b> (כל טיסה / נורמלית)"]
    for d in config.DATES:
        iso = d.isoformat()
        day = [c for c in combined if c.date == iso]
        if not day:
            lines.append(f"{d_he(iso)}: אין נתונים")
            continue
        n = next((c for c in day if c.is_normal()), None)
        lines.append(f"{d_he(iso)}: <b>{usd(day[0].usd)}</b> / {usd(n.usd) + ' ' + escape(n.dep) if n else '—'}")
    out.append("\n".join(lines))

    # 6. changes
    lines = [f"📈 <b>שינוי מאתמול</b> (±${config.CHANGE_ALERT_USD}+)"]
    if not chg.get("prev_run"):
        lines.append("ריצה ראשונה – אין השוואה.")
    else:
        for c, pv, delta in chg["flights"][:6]:
            arrow = "🔻" if delta < 0 else "🔺"
            lines.append(f"{arrow} {escape(label(c))}: {usd(pv)} → {usd(c.usd)} ({delta:+d}$)")
        for d, pv, delta in chg["dates"]:
            arrow = "🔻" if delta < 0 else "🔺"
            lines.append(f"{arrow} מינימום {d_he(d)}: {usd(pv)} → {usd(pv + delta)}")
        if chg["cheapest"]:
            pv, delta = chg["cheapest"]
            lines.append(f"{'🔻' if delta < 0 else '🔺'} הכי זול כולל: {usd(pv)} → {usd(pv + delta)}")
        if len(lines) == 1:
            lines.append("אין שינויים משמעותיים.")
    out.append("\n".join(lines))

    # 7. sites
    ok = [r for r in results if r.status == "ok"]
    bad = [r for r in results if r.status != "ok"]
    lines = ["🌐 <b>אתרים</b>"]
    if ok:
        lines.append("✅ " + ", ".join(f"{r.site.label} ({len(r.dates_ok)}/{len(config.DATES)})" for r in ok))
    if bad:
        reason = {"not reachable": "חסום/בוט", "no results": "אין תוצאות", "error": "שגיאה", "not run": "לא רץ"}
        lines.append("❌ " + ", ".join(f"{r.site.label} – {reason.get(r.status, r.status)}" for r in bad))
    if inactive:
        lines.append("⛔ לא נגישים בבדיקה (לא נסרקים): " + ", ".join(inactive))
    out.append("\n".join(lines))
    return "\n\n".join(out)


def to_markdown(html: str) -> str:
    md = re.sub(r'<a href="([^"]+)">([^<]+)</a>', lambda m: f"[{m.group(2)}]({m.group(1).replace('&amp;', '&')})", html)
    md = re.sub(r"</?b>", "**", md)
    md = md.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#x27;", "'")
    # keep line breaks inside paragraphs on GitHub
    return "\n".join(l + "  " if l else l for l in md.splitlines()) + "\n"
