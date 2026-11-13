"""Send the report through the Telegram Bot API (HTML parse mode)."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

LIMIT = 4000  # Telegram's hard limit is 4096 chars per message


def split(text: str, limit: int = LIMIT) -> list[str]:
    parts, cur = [], ""
    for block in text.split("\n\n"):
        if len(cur) + len(block) + 2 > limit and cur:
            parts.append(cur)
            cur = ""
        cur = f"{cur}\n\n{block}" if cur else block
    if cur:
        parts.append(cur)
    return parts


def send(html: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets not set; skipping send.")
        return False
    ok = True
    for part in split(html):
        data = urllib.parse.urlencode({"chat_id": chat, "text": part, "parse_mode": "HTML",
                                       "disable_web_page_preview": "true"}).encode()
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30) as r:
                ok &= json.load(r).get("ok", False)
        except urllib.error.HTTPError as e:
            print("Telegram error:", e.code, e.read()[:300])
            ok = False
    print("Telegram sent." if ok else "Telegram send FAILED.")
    return ok
