"""What the screen asks Jev about a guest's message, and how sure Jev must be.

Kept in one file so the wording and the threshold are easy to review and
tune. Each question is one judgment a person could make at a glance; code
decides the route from the answers (`screen.route_from`).
"""

from __future__ import annotations

from typing import Final

from typesafe_sdk import Noul, NoulCriteria

JEV_MODEL: Final = "jev-1.14.0"
"""Pinned, not `jev-latest`: the threshold below was tuned on this version."""

YES: Final = 0.7
"""A question counts as yes at this probability or above.

Tuned on 2026-10-28 over 35 messages, English and Indonesian: every
emergency and staff request scored 0.81 or more on its question, and every
everyday look-alike 0.43 or less ("Who is the manager here?" on wants_staff).
"""

SETTING: Final = (
    "A guest speaks to Wayan, a voice kiosk in the lobby of a hotel in Bali."
)


def _noul(instructions: str, yes: str, no: str) -> Noul:
    return Noul(instructions=instructions, criteria=NoulCriteria(true=yes, false=no))


EMERGENCY_QUESTIONS: Final = {
    "someone_hurt": _noul(
        "Does `guest_message` say that someone is hurt or suddenly ill right now "
        "and needs medical help?",
        yes="Someone is injured, bleeding, collapsed, unconscious, struggling to "
        "breathe, or suddenly very ill at this moment.",
        no="Nobody needs medical help now: the guest asks a question, chats, or "
        "mentions mild aches, a past injury, or a story.",
    ),
    "danger": _noul(
        "Does `guest_message` report a fire, smoke, or another danger happening at "
        "the hotel right now?",
        yes="The guest reports a fire, smoke, a burning smell, or another present "
        "danger.",
        no="The guest asks about fire dances, history, or anything else with no "
        "present danger.",
    ),
    "person_missing": _noul(
        "Does `guest_message` say that a person who is with the guest is lost or "
        "missing right now?",
        yes="A child, relative, or companion of the guest cannot be found right now.",
        no="Nobody is missing: the guest lost an object, or tells a story.",
    ),
}

STAFF_QUESTIONS: Final = {
    "wants_staff": _noul(
        "Does the guest in `guest_message` ask to talk to a hotel staff member or "
        "a real person instead of the kiosk?",
        yes="The guest asks for a staff member, the front desk, a manager, or a real "
        "person to help them.",
        no="The guest asks the kiosk itself, or only mentions or asks about staff "
        "without asking to talk to them.",
    ),
}

QUESTIONS: Final = {**EMERGENCY_QUESTIONS, **STAFF_QUESTIONS}
