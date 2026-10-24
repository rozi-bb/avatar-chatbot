"""The message screen: spots emergencies and requests for a person by rules.

It runs before the model on every message, so it must be instant: keyword
rules, not a second model call (docs/architecture.md §4.2). The patterns are
narrow on purpose, because "help" and "fire" also turn up in everyday
questions ("can you help me find the spa?", "the fire dance"). What they
miss, the model catches with its [help] tag.
"""

from __future__ import annotations

import re
from typing import Literal

Route = Literal["normal", "emergency", "staff"]

MAX_GUEST_CHARS = 300
"""A guest's message is cut to this length before anything reads it."""

PEOPLE = r"(?:child|son|daughter|kid|baby|boy|girl|little one|grandma|grandpa|mum|mom|dad|wife|husband|friend)"

EMERGENCY = re.compile(
    rf"""
    \b(?:emergency|ambulance|bleeding|unconscious|fainted|passed\ out|heart\ attack|
        seizure|choking|drowning|overdose|stroke)\b
    | \b(?:can'?t|cannot|not|isn'?t|is\ not)\ breath(?:e|ing)\b
    | \b(?:call|get)\ (?:a\ |an\ |the\ )?(?:doctor|ambulance|police)\b
    | \b(?:is|are|got|been|badly|seriously|i'?m|i\ am|he'?s|she'?s|they'?re)\ (?:hurt|injured)\b
    | \b(?:fell|fallen)\ (?:down|over|in|into)\b
    | \b(?:there'?s|there\ is)\ (?:a\ )?fire\b | \bon\ fire\b | \bfire\ alarm\b
    | \bsomething'?s\ burning\b | \bsmell(?:s|ing)?\ (?:of\ )?smoke\b
    | \b(?:lost|missing|can'?t\ find)\ (?:my|our|a)\ (?:little\ )?{PEOPLE}\b(?!'s)
    | \b{PEOPLE}\ (?:is|has\ gone|has\ been|went|got)\ (?:lost|missing)\b
    | ^\W*(?:help|help\ me|somebody\ help|someone\ help)\W*$
    | \b(?:somebody|someone)\ help\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

STAFF = re.compile(
    r"""
    \b(?:talk|speak|chat)\ (?:to|with)\ (?:a\ |an\ |the\ |some\ )?(?:real\ |actual\ |human\ )?
        (?:person|human|staff|someone|somebody|manager|receptionist|people)\b
    | \b(?:real|actual)\ (?:person|human)\b
    | \b(?:call|get|need|want)\ (?:me\ )?(?:a\ |an\ |the\ )?(?:staff\ member|staff|manager|receptionist|human)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def screen(text: str) -> Route:
    """Return where a guest's message should go: the model, or a fixed reply."""
    if EMERGENCY.search(text):
        return "emergency"
    if STAFF.search(text):
        return "staff"
    return "normal"
