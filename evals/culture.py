"""The `wayan-culture` suite: Balinese culture, from the curated notes."""

from __future__ import annotations

from typing import Any

from evals.checks import format_valid, guest, has_facts

DATASET = "wayan-culture"
DESCRIPTION = "Balinese culture from knowledge/bali-culture.md, in kid-friendly words."


def ask(question: str, *facts: list[str]) -> dict[str, Any]:
    """Return one example: a question and the facts its answer must hold."""
    return {"inputs": guest(question), "outputs": {"facts": list(facts)}}


EXAMPLES: list[dict[str, Any]] = [
    ask("What is Nyepi?", ["silence", "silent", "quiet"]),
    ask("What does Galungan celebrate?", ["good"], ["evil", "bad"]),
    ask("What are those little flower trays on the ground everywhere?", ["canang"]),
    ask("Why is your name Wayan?", ["first"]),
    ask("How do you say thank you in Balinese?", ["suksma"]),
    ask("What is subak?", ["water"]),
    ask("What is the kecak dance?", ["cak", "chant"]),
    ask("What's babi guling?", ["pig", "pork"]),
]

EVALUATORS = [format_valid, has_facts]
TARGETS = {"format_valid": 1.0, "has_facts": 0.9}
"""Minimum share of passing examples."""
