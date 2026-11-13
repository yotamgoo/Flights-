"""Site definition shared by all extractors."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

BLOCK_PATTERNS = re.compile(
    r"captcha|are you a (human|robot)|what is a bot|bot or not|access denied|access to this page has been denied"
    r"|just a moment|verify you are human|unusual traffic|press (and|&) hold|our systems have detected"
    r"|request blocked|pardon our interruption",
    re.I,
)


class Blocked(Exception):
    """Site showed a captcha / bot check."""


@dataclass
class Site:
    name: str                     # short id, e.g. "google"
    label: str                    # display name
    url_fn: Callable[[date], str]
    extract: Callable | None = None        # (page, date, captured) -> list[Flight]
    capture: Callable[[str], bool] | None = None  # response-url predicate for JSON capture
    ready_selector: str | None = None      # wait for this before extracting
    wait_ms: int = 30_000                  # max wait for results to render
    settle_ms: int = 4_000                 # extra settle time once ready
    locale: str = "en-US"
    notes: str = ""

    def url(self, d: date) -> str:
        return self.url_fn(d)


def check_blocked(status: int | None, title: str, body: str, url: str) -> str | None:
    if status in (401, 403, 405, 429, 432, 503):
        return f"HTTP {status}"
    hay = f"{title}\n{body[:3000]}\n{url}"
    m = BLOCK_PATTERNS.search(hay)
    if m:
        return f"bot check ({m.group(0)})"
    if re.search(r"/captcha|/sorry/|bots\.html|px/captcha", url):
        return "bot check (redirect)"
    return None


def load_json(body: bytes):
    try:
        return json.loads(body)
    except Exception:
        return None
