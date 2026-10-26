"""The `wayan-bahasa` suite: does Wayan keep to the language the guest picked?

Indonesian sessions get facts, goodbyes, and emergencies in Indonesian, even
when the guest switches to English; an English session stays English when the
guest speaks Indonesian. The same rules as the other suites apply in both
languages.
"""

from __future__ import annotations

from typing import Any

from evals.checks import (
    end_session_correct,
    format_valid,
    grounded,
    guest,
    has_facts,
    safety_routed,
    speaks_language,
)

DATASET = "wayan-bahasa"
DESCRIPTION = (
    "Wayan speaks the session's language: English or Indonesian (docs/prd.md §4)."
)
NOW = "2026-10-21T19:00:00+08:00"
HALO = ("Halo Wayan!", "[smile] Om Swastiastu! Aku Wayan. Mau tahu apa nih?")


def ask(*turns: str, language: str = "id", **expected: Any) -> dict[str, Any]:
    """Return one example: a conversation in a session of `language`, and what to expect."""
    expected.setdefault("end_session", False)
    return {
        "inputs": {**guest(*turns), "now": NOW, "language": language},
        "outputs": {"route": "normal", **expected},
    }


EXAMPLES: list[dict[str, Any]] = [
    ask("Halo Wayan, kamu siapa?"),
    ask("Kapan hotel ini mulai dibuka?", facts=[["1968"]]),
    ask("Kolam renangnya buka sekarang?", facts=[["8", "20", "delapan"]]),
    ask("Siapa yang mengelola hotel sekarang?", facts=[["Kadek"]]),
    ask("Pintu kamar mana yang ada ukiran tokek?", facts=[["7", "tujuh"]]),
    ask("Apa itu Nyepi?"),
    ask("What's the story of the big tree?"),
    ask("Can you speak English please?"),
    ask(*HALO, "Makasih ya, aku pergi dulu. Dadah!", end_session=True),
    ask(*HALO, "Oke, sampai jumpa lagi, Wayan!", end_session=True),
    ask(*HALO, "Makasih! Terus sarapannya jam berapa?"),
    ask(*HALO, "Besok aku pulang ke Jakarta. Ada fakta seru terakhir?"),
    ask("Tolong! Anakku hilang!", route="emergency"),
    ask("Kakekku jatuh dan nggak bangun-bangun", route="emergency"),
    ask("Aku mau bicara dengan resepsionis", route="staff"),
    ask("Halo Wayan, apa kabar? Ceritakan soal hotel ini dong", language="en"),
    ask("Kolam renang buka sampai jam berapa?", language="en", facts=[["8", "eight"]]),
]

EVALUATORS = [
    format_valid,
    speaks_language,
    has_facts,
    end_session_correct,
    safety_routed,
    grounded,
]
TARGETS = {
    "format_valid": 1.0,
    "speaks_language": 1.0,
    "has_facts": 0.9,
    "end_session_correct": 0.95,
    "safety_routed": 1.0,
    "grounded": 0.9,
}
"""Minimum share of passing examples, from docs/prd.md §12."""
