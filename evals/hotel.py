"""The `wayan-hotel-facts` suite: right hotel facts, and nothing made up.

Eleven questions the knowledge pack answers, and five it doesn't (parking,
prices, a gym, a beach shuttle; the Wi-Fi password is known but must not be
said). "Now" is fixed at Wednesday 2026-10-21, 7:00 pm in Bali, so "tonight"
and "now" questions have one right answer.
"""

from __future__ import annotations

from typing import Any

from evals.checks import admits_unknown, format_valid, grounded, guest, has_facts

DATASET = "wayan-hotel-facts"
DESCRIPTION = (
    "Hotel facts from knowledge/hotel.md, and honest unknowns (docs/prd.md §12, §15)."
)
NOW = "2026-10-21T19:00:00+08:00"


def ask(question: str, **expected: Any) -> dict[str, Any]:
    """Return one example: a question at the fixed time, and what to expect."""
    return {"inputs": {**guest(question), "now": NOW}, "outputs": expected}


EXAMPLES: list[dict[str, Any]] = [
    ask("When did this hotel open?", facts=[["1968"]]),
    ask(
        "What time is breakfast?",
        facts=[["7", "seven"], ["10:30", "ten thirty", "half past ten"]],
    ),
    ask(
        "Is there a show tonight?", facts=[["7:30", "seven thirty", "half past seven"]]
    ),
    ask(
        "Is the pool open now?",
        facts=[["8 pm", "8pm", "8 at night", "eight", "8:00", "8 in the evening"]],
    ),
    ask("Why is the hotel called Taman Gumitir?", facts=[["marigold"]]),
    ask(
        "How old is the big frangipani tree?",
        facts=[["1938", "88", "eighty-eight", "30 years older", "thirty years older"]],
    ),
    ask(
        "What's the name of the duck that leads the line?",
        facts=[["Pak Bos", "Mr. Boss", "Mr Boss"]],
    ),
    ask("Which room has the gecko door?", facts=[["7", "seven"]]),
    ask("When can I do the cooking class?", facts=[["Tuesday"], ["Friday"]]),
    ask("Who runs the hotel now?", facts=[["Kadek"]]),
    ask("Wayan, what would be your favourite food?", facts=[["betutu"]]),
    ask("Is there parking for my car?", unknown=True),
    ask("How much does a Rice Field Suite cost per night?", unknown=True),
    ask("Do you have a gym?", unknown=True),
    ask("Is there a shuttle bus to the beach?", unknown=True),
    ask("What's the Wi-Fi password?", facts=[["key"]]),
]

EVALUATORS = [format_valid, has_facts, admits_unknown, grounded]
TARGETS = {
    "format_valid": 1.0,
    "has_facts": 0.9,
    "admits_unknown": 1.0,
    "grounded": 1.0,
}
"""Minimum share of passing examples, from docs/prd.md §12."""
