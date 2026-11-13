from . import agoda, booking, google, opodo, priceline
from .probe_only import SITES as PROBE_ONLY

# Sites with a working extractor, in the order they are scraped.
ACTIVE = [google.SITE, opodo.SITE, agoda.SITE, booking.SITE, priceline.SITE]
ALL = ACTIVE + PROBE_ONLY
BY_NAME = {s.name: s for s in ALL}
