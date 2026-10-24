"""An estimate of today's spend, so a public demo can't run up a bill.

Estimated, not billed: DeepSeek tokens at peak prices and Azure TTS per
character (docs/prd.md §13). It lives in memory, so a restart resets it.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

BALI = ZoneInfo("Asia/Makassar")

# US dollars per token or character, at the highest listed rates (2026-10-24).
INPUT_MISS = 0.30 / 1_000_000
INPUT_HIT = 0.006 / 1_000_000
OUTPUT = 1.20 / 1_000_000
TTS_CHAR = 22 / 1_000_000


def reply_cost(usage: dict[str, Any] | None, spoken: str) -> float:
    """Estimate one reply's cost from its token usage and the text Wayan speaks."""
    usage = usage or {}
    cached = (usage.get("input_token_details") or {}).get("cache_read", 0) or 0
    fresh = max(usage.get("input_tokens", 0) - cached, 0)
    words = re.sub(r"\[[a-z]+\]", "", spoken).strip()
    return float(
        fresh * INPUT_MISS
        + cached * INPUT_HIT
        + usage.get("output_tokens", 0) * OUTPUT
        + len(words) * TTS_CHAR
    )


class DailyBudget:
    """Adds up today's estimated spend (Bali days) against an optional cap."""

    def __init__(self, limit_usd: float | None) -> None:
        """Set the cap; None means no cap."""
        self.limit = limit_usd
        self.day: date = datetime.now(BALI).date()
        self.spent = 0.0

    def _roll(self) -> None:
        today = datetime.now(BALI).date()
        if today != self.day:
            self.day, self.spent = today, 0.0

    def add(self, cost: float) -> None:
        """Count a cost against today."""
        self._roll()
        self.spent += cost

    def used_up(self) -> bool:
        """Return True when today's cap is reached."""
        self._roll()
        return self.limit is not None and self.spent >= self.limit
