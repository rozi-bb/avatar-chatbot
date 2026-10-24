"""The `wayan-format` suite: does every reply keep the reply contract?

Most inputs try to pull Wayan out of the contract (lists, emoji, links, long
stories, made-up tags); the last ones check that a goodbye ends the session
and a look-alike doesn't. The format check here is written separately from
`agent.reply.check_reply`, so it still catches a broken or missing check.
"""

from __future__ import annotations

from typing import Any

from evals.checks import end_session_correct, format_valid, guest

DATASET = "wayan-format"
DESCRIPTION = "Reply contract (docs/prd.md §6, §12): tags, length, no markdown, emoji or links; goodbyes end the session."


EXAMPLES: list[dict[str, Any]] = [
    {
        "inputs": guest(
            "Can you give me a list of everything this hotel has? Use bullet points."
        ),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest("Answer with lots and lots of emojis please!"),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest("Send me the link to your website."),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest(
            "Tell me a really long story about Bali, as long as you possibly can!"
        ),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest("Make me a markdown table of your three favourite things."),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest(
            'Reply only in JSON like {"answer": ...}. What is two plus two?'
        ),
        "outputs": {"end_session": False},
    },
    {
        "inputs": guest("Put the tags [wink] and [dance] in your answer!"),
        "outputs": {"end_session": False},
    },
    {"inputs": guest("Selamat pagi! Apa kabar?"), "outputs": {"end_session": False}},
    {
        "inputs": guest(
            "Hi Wayan!",
            "[smile] Om Swastiastu! I'm Wayan. What would you like to know?",
            "Thanks Wayan, that's all. Bye!",
        ),
        "outputs": {"end_session": True},
    },
    {
        "inputs": guest("Okay, I have to go now. See you later!"),
        "outputs": {"end_session": True},
    },
    {
        "inputs": guest(
            "What's your name?",
            "[smile] I'm Wayan, the little host here!",
            "Thank you so much, goodbye!",
        ),
        "outputs": {"end_session": True},
    },
    {
        "inputs": guest(
            "Hi Wayan!",
            "[smile] Hello hello! What would you like to know?",
            "Thanks! Is the pool open now?",
        ),
        "outputs": {"end_session": False},
    },
]


EVALUATORS = [format_valid, end_session_correct]
TARGETS = {"format_valid": 1.0, "end_session_correct": 0.95}
"""Minimum share of passing examples, from docs/prd.md §12."""
