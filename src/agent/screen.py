"""The message screen: spots emergencies and requests for a person.

It runs before the model on every message, in two layers
(docs/architecture.md §4.2). Keyword rules go first: they are instant and
work with no network, so a clear "call an ambulance" never waits on an API.
The patterns are narrow on purpose, because "help" and "fire" also turn up
in everyday questions ("can you help me find the spa?", "the fire dance").

A message the rules let through gets a second look from Jev, which catches
what no keyword list can ("my husband just collapsed"). Jev only answers
typed questions (`screen_questions`); code picks the route. If Jev fails or
is slow, the message goes on as normal, and the model's [help] tag is the
last net.

Each rule has an English and an Indonesian set, and both always apply: a
guest may speak either language, whichever one the kiosk was set to. The
Indonesian ones stay just as narrow: "tolong" alone is a cry for help, but
"tolong ceritakan..." only means "please tell...".
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeError

from agent.screen_questions import (
    EMERGENCY_QUESTIONS,
    JEV_MODEL,
    QUESTIONS,
    SETTING,
    STAFF_QUESTIONS,
    YES,
)

log = logging.getLogger(__name__)

Route = Literal["normal", "emergency", "staff"]

Judge = Callable[[str], Awaitable[Mapping[str, float]]]
"""Answers the screen's questions about a message: question ID to P(yes)."""

JEV_WAIT = 1.5
"""Seconds the screen waits for Jev before letting the message through.

Measured 2026-10-28: 0.35 s median and 0.5 s p90 on a warm connection, about
1 s for the first call.
"""

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


ORANG = r"(?:anak|anakku|adik|adikku|bayi|cucu|cucuku|ibu|ibuku|bapak|ayah|ayahku|nenek|kakek|istri|istriku|suami|suamiku|teman|temanku)"
NAPAS = r"(?:napas|nafas|bernapas|bernafas)"

EMERGENCY_ID = re.compile(
    rf"""
    \b(?:darurat|ambulans|ambulan|pingsan|berdarah|pendarahan|kejang|tersedak|keselek|
        tenggelam|overdosis|serangan\ jantung|kebakaran|alarm\ kebakaran)\b
    | \b(?:tidak|tak|gak|ga|nggak|ngga|enggak)\ bisa\ {NAPAS}\b | \b(?:sesak|susah)\ {NAPAS}\b
    | \b(?:panggil|panggilkan|telepon|telpon|teleponkan)\ (?:dokter|ambulans|ambulan|polisi|pemadam|damkar)\b
    | \b(?:terluka|luka\ parah|cedera)\b
    | \b(?:terjatuh|jatuh\ (?:dari|ke|di))\b
    | \bada\ (?:api|asap)\b | \bbau\ (?:asap|gosong|terbakar)\b
    | \b{ORANG}(?:\ (?:saya|aku|kami|kita))?\ (?:hilang|tersesat|nyasar)\b | \bkehilangan\ {ORANG}\b
    | ^\W*(?:tolong|tolongin|tolong\ (?:aku|saya|kami)|tolongin\ (?:aku|saya))\W*$
    | \b(?:siapa\ saja|siapapun|seseorang)\ tolong\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

STAFF_ROLE = r"(?:staf|staff|petugas|karyawan|pegawai|resepsionis|manajer|manager)"

STAFF_ID = re.compile(
    rf"""
    \b(?:bicara|berbicara|ngomong|ngobrol|bertemu|ketemu)\ (?:sama|dengan|ke)
        \ (?:manusia|orang\ (?:beneran|sungguhan)|{STAFF_ROLE})\b
    | \bmanusia\ (?:beneran|asli|sungguhan)\b | \borang\ (?:beneran|sungguhan)\b
    | \b(?:panggil|panggilkan|minta|butuh|perlu|mau|ingin)\ (?:ke\ )?{STAFF_ROLE}\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def screen(text: str) -> Route:
    """Return where a guest's message should go: the model, or a fixed reply."""
    if EMERGENCY.search(text) or EMERGENCY_ID.search(text):
        return "emergency"
    if STAFF.search(text) or STAFF_ID.search(text):
        return "staff"
    return "normal"


def route_from(answers: Mapping[str, float]) -> Route:
    """Pick a route from Jev's answers; an emergency outranks a staff request."""
    if any(answers[q] >= YES for q in EMERGENCY_QUESTIONS):
        return "emergency"
    if any(answers[q] >= YES for q in STAFF_QUESTIONS):
        return "staff"
    return "normal"


async def second_look(text: str, judge: Judge) -> Route:
    """Ask Jev about a message the keyword rules let through.

    A failed or slow call is not an answer, so it is logged, never read as a
    "no"; the message still goes on to Wayan, whose [help] tag can catch it.
    """
    try:
        async with asyncio.timeout(JEV_WAIT):
            answers = await judge(text)
    except (TypeSafeError, TimeoutError) as error:
        log.warning("Jev screen skipped: %s", type(error).__name__)
        return "normal"
    return route_from(answers)


class Jev:
    """The screen's questions, asked of TypeSafe's Jev over one kept-open client."""

    def __init__(self) -> None:
        """Prepare Jev; the client is opened on the first call."""
        self._client: AsyncTypeSafeClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def __call__(self, text: str) -> dict[str, float]:
        """Ask the screen's questions about a guest's message.

        Args:
            text: The guest's message, already cut to size.

        Returns:
            Each question's ID with Jev's probability that the answer is yes.
        """
        # Made on the first call, so a missing API key fails inside
        # second_look, where it is caught, not when the graph is built. Made
        # again on a new event loop (evals and tests start one per run),
        # because the client's connections belong to the loop that opened them.
        loop = asyncio.get_running_loop()
        if self._client is None or self._loop is not loop:
            # No retries: a retry would not fit in JEV_WAIT anyway.
            self._client = AsyncTypeSafeClient(
                model=JEV_MODEL, retry=RetryPolicy(max_retries=0)
            )
            self._loop = loop
        response = await self._client.system_one(
            state={"setting": SETTING, "guest_message": text}, questions=QUESTIONS
        )
        return {q: response.nouls[q].noul for q in QUESTIONS}
