"""Trip definition and run settings."""
from datetime import date, timedelta

ORIGIN, DEST = "TLV", "CMB"
FIRST_DATE = date(2026, 11, 25)
LAST_DATE = date(2026, 12, 1)
# The workflow stops (and disables itself) after this day.
STOP_AFTER = date(2026, 12, 1)

DATES = [FIRST_DATE + timedelta(days=i) for i in range((LAST_DATE - FIRST_DATE).days + 1)]

# Report thresholds
NORMAL_MAX_MIN = 12 * 60 + 15      # "under ~12h"
REASONABLE_MAX_MIN = 20 * 60       # "under ~20h"
OVERNIGHT_LAYOVER_MIN = 8 * 60     # any layover this long counts as overnight
CHANGE_ALERT_USD = 30

# Politeness
DELAY_RANGE_S = (3.0, 5.0)
PAGE_TIMEOUT_MS = 60_000

FALLBACK_EUR_USD = 1.16
