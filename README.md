# TLV → CMB daily flight price tracker

A free, fully cloud tracker. Every morning a GitHub Actions job opens the flight-search sites in headless
Chromium (Playwright), reads the results, and sends a short Hebrew report to your Telegram.

* **Trip:** one-way, 1 adult, economy, Tel Aviv (TLV) → Colombo (CMB), departing any day **25 Nov – 1 Dec 2026**
* **When:** daily at **05:30 UTC (07:30 Israel)**. You can also start it manually (*Actions → daily-flight-prices → Run workflow*)
* **Stops by itself:** the first run after 1 Dec 2026 disables the workflow
* **Cost:** $0 (GitHub Actions free minutes + the Telegram Bot API). Your computer doesn't need to be on
* It never books, pays or logs in to anything

---

## Setup (about 5 minutes)

### 1. Create the Telegram bot (BotFather)
1. In Telegram, open a chat with **@BotFather** (blue check mark).
2. Send `/newbot`.
3. Enter a display name, e.g. `TLV CMB prices`.
4. Enter a username that ends in `bot`, e.g. `tlv_cmb_prices_bot`.
5. BotFather replies with a **token** like `1234567890:AAH...`. This is your `TELEGRAM_BOT_TOKEN`. Keep it secret.

### 2. Get your chat id
1. Open your new bot in Telegram (BotFather's message links to it) and press **Start**, or send it any message, e.g. `hi`.
2. In a browser, open (replace `<TOKEN>` with your token):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. In the JSON, find `"chat":{"id":123456789,...}`. That number is your `TELEGRAM_CHAT_ID`.
   * If you see `"result":[]`, send the bot another message and reload.
   * For a group, add the bot to the group, send a message there, and use the group id (a negative number such as `-100…`).

### 3. Add the repo secrets
In this GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**. Add two secrets:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | the number from `getUpdates` |

### 4. Make sure Actions can run and write
* **Actions → enable workflows** if GitHub asks.
* **Settings → Actions → General → Workflow permissions → "Read and write permissions"**. The job commits
  `data/last_run.json` (yesterday's prices) back to the repo.
* The schedule runs from the repo's **default branch**. If you move the code to another branch (e.g. `main`), make
  that branch the default.

### 5. Test it
**Actions → daily-flight-prices → Run workflow**. A full run takes about 20–30 minutes (one page at a time, 3–5 s
apart). The report arrives in Telegram and is also saved as the run's **artifact** (`report.md`, plus
`results.json` with every flight found).

---

## What the report contains (Hebrew, phone-sized)
1. **המלצה היום** – one line
2. **טיסות נורמליות** – 1 stop, under ~12 h, no overnight layover; up to 5, cheapest first, with price on each site and a link to the cheapest
3. **זולות אבל סבירות** – up to 2 stops, under ~20 h, no overnight; up to 4, each marked one ticket / separate tickets
4. **הכי זול שיש** – the absolute cheapest, whatever it takes
5. Cheapest price per departure date (any flight / normal flight)
6. Change vs yesterday – moves of **$30+** (per flight, per date, overall)
7. Which sites worked and which failed

The same flight on several sites (same date + departure/arrival times + connection airports) is merged into one row.
EUR prices are converted to USD with the day's ECB rate (frankfurter.app).

"Overnight layover" means a connection of 8 h or more, or one of 3 h or more that covers 01:00–05:00.

The first report compares against the manual **13 Nov 2026 baseline** (`data/baseline.json`, copied to
`data/last_run.json`).

---

## Site status

Tested 13 Nov 2026, from this project's cloud container and from a GitHub Actions runner (the place that matters).
No stealth plugins, fingerprint spoofing, proxies or captcha solvers are used. A site that shows a bot check is
marked *not reachable* and skipped.

| Site | GitHub Actions | How it's read | Status |
|---|---|---|---|
| Google Flights | ✅ results | result cards (aria-labels) | **active** |
| Opodo | ✅ results | the page's own itinerary JSON | **active** |
| Agoda | ✅ results | the page's own flights JSON | **active** |
| Booking.com | ⚠️ page loads (after an AWS-WAF check) but says "We don't have any flights matching your search" | the page's own flights JSON | **active** (gives up after 2 empty dates) |
| Priceline | ❌ 403 PerimeterX "Press & Hold" on Actions (worked from the test container) | server-rendered state | **active** (skipped automatically while blocked) |
| Kayak / Momondo / Cheapflights | ❌ redirect to "What is a bot?" | – | inactive |
| Skyscanner | ❌ PerimeterX captcha | – | inactive |
| Kiwi.com | ❌ HTTP 403 | – | inactive |
| Expedia | ❌ HTTP 429 "Bot or Not?" | – | inactive |
| Trip.com | ❌ HTTP 432 | – | inactive |
| Aviasales | ❌ AWS-WAF + reCAPTCHA, results never load | – | inactive |
| Skiplagged / FlightHub / JustFly | ❌ Cloudflare "Just a moment…" | – | inactive |
| CheapOair | ❌ results URL redirects to the home page | – | inactive |
| Etihad.com | ❌ blank page (Akamai bot manager) | – | inactive |
| Issta | ❌ Reblaze bot challenge, blank page (results URL: `/flights/results.aspx?route=1&…`) | – | inactive |
| Gulliver | no deep-link results URL found | – | not added |
| Daka90 | HTTP 403 on the home page | – | not added |

To re-check every site at any time: **Actions → probe-sites → Run workflow**. The table appears in the run summary.
Active sites that hit a bot check are retried once per day, then skipped for that run, so they cost about 30 s.

---

## Run locally (optional)
```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && python -m playwright install chromium
python -m tracker probe                                          # reachability table, one date
python -m tracker run --no-send --no-save                        # full report to stdout + report.md
python -m tracker run --sites google,opodo --dates 2026-11-27 --no-send --no-save
```
Set `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` in the environment to send from your machine.

## Layout
```
tracker/
  config.py        trip dates, thresholds, delays
  scrape.py        one page at a time, waits for results, bot-check detection, 3–5 s delays
  sites/           one extractor per site (google, opodo, agoda, booking, priceline) + probe-only list
  aggregate.py     USD conversion, de-duplication across sites, normal/reasonable rules
  history.py       data/last_run.json → "change vs yesterday"
  report.py        Hebrew report (Telegram HTML + Markdown)
  telegram.py      Bot API sender (splits >4000 chars)
.github/workflows/
  daily.yml        cron 05:30 UTC + manual; commits data/last_run.json; disables itself after 1 Dec
  probe.yml        manual reachability check of every site
```
