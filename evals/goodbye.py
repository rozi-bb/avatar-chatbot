"""The `wayan-goodbye` suite: does the session end exactly when the guest leaves?

Real goodbyes in many wordings, and look-alikes that thank Wayan, mention
leaving, or talk about the word "bye" while the guest still wants to chat.
"""

from __future__ import annotations

from typing import Any

from evals.checks import ends_on_goodbye, format_valid, guest, no_false_end

DATASET = "wayan-goodbye"
DESCRIPTION = "Goodbyes end the session; look-alikes don't (docs/prd.md §4, §12)."
HELLO = ("Hi Wayan!", "[smile] Om Swastiastu! I'm Wayan. What would you like to know?")


def says(text: str, *, leaving: bool) -> dict[str, Any]:
    """Return one example: a guest's next message after a hello, and whether they're leaving."""
    return {"inputs": guest(*HELLO, text), "outputs": {"end_session": leaving}}


EXAMPLES: list[dict[str, Any]] = [
    says("Bye!", leaving=True),
    says("Thanks Wayan, see you later!", leaving=True),
    says("I have to go now, my taxi is here.", leaving=True),
    says("Okay, that's all. Thank you!", leaving=True),
    says("Good night Wayan!", leaving=True),
    says("See ya, little buddy!", leaving=True),
    says("We're off to the pool now. Bye bye!", leaving=True),
    says("Thank you so much, goodbye!", leaving=True),
    says("Thanks! What else is there to do here?", leaving=False),
    says("Thank you! And when is breakfast?", leaving=False),
    says("How do you say goodbye in Balinese?", leaving=False),
    says("My friend just left. Can you tell me a joke?", leaving=False),
    says("I'll go to the pool later. When does it close?", leaving=False),
    says("Good morning Wayan!", leaving=False),
    says("Wait, before I go, how old is the big tree?", leaving=False),
    says("I'm leaving Bali tomorrow. Any last fun fact?", leaving=False),
]

EVALUATORS = [format_valid, ends_on_goodbye, no_false_end]
TARGETS = {"format_valid": 1.0, "ends_on_goodbye": 0.95, "no_false_end": 0.95}
"""Minimum share of passing examples, from docs/prd.md §12."""
