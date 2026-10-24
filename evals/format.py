"""The `wayan-format` suite: does every reply keep the reply contract?

Most inputs try to pull Wayan out of the contract (lists, emoji, links, long
stories, made-up tags); the last ones check that a goodbye ends the session
and a look-alike doesn't. The format check here is written separately from
`agent.reply.check_reply`, so it still catches a broken or missing check.
"""

from __future__ import annotations

import re
from typing import Any

from agent.reply import MAX_CHARS, SPOKEN_TAGS

DATASET = "wayan-format"
DESCRIPTION = "Reply contract (docs/prd.md §6, §12): tags, length, no markdown, emoji or links; goodbyes end the session."


def guest(*turns: str) -> dict[str, Any]:
    """Return dataset inputs for a conversation; alternate turns are Wayan's."""
    roles = ["user", "assistant"]
    return {
        "messages": [
            {"role": roles[i % 2], "content": text} for i, text in enumerate(turns)
        ]
    }


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


def format_problems(text: str) -> list[str]:
    """Return every way `text` breaks the reply contract; empty when it's fine."""
    problems = []
    tags = re.findall(r"\[([^\]]*)\]", text)
    if not re.match(r"\[[a-z]+\]", text):
        problems.append("doesn't start with a tag")
    if bad := [t for t in tags if t not in SPOKEN_TAGS]:
        problems.append(f"tags not allowed: {bad}")
    if len(text) > MAX_CHARS:
        problems.append(f"{len(text)} characters, over {MAX_CHARS}")
    if re.search(r"[*#`|_~]|\n|^\s*[-•]\s|\(http", text, re.M):
        problems.append("markdown")
    if re.search(r'[{}]|"\s*\w+"\s*:', text):
        problems.append("JSON")
    if re.search(r"https?://|www\.", text, re.I):
        problems.append("link")
    if re.search("[\U0001f000-\U0001faff☀-➿]", text):
        problems.append("emoji")
    if not re.search(r"[A-Za-z]", re.sub(r"\[[^\]]*\]", "", text)):
        problems.append("nothing to say")
    return problems


def format_valid(outputs: dict[str, Any]) -> dict[str, Any]:
    """Code evaluator: the reply keeps the contract."""
    problems = format_problems(outputs["reply"])
    return {
        "key": "format_valid",
        "score": not problems,
        "comment": "; ".join(problems) or "ok",
    }


def end_session_correct(
    outputs: dict[str, Any], reference_outputs: dict[str, Any]
) -> dict[str, Any]:
    """Code evaluator: the session ends exactly when the guest is leaving."""
    expected = reference_outputs["end_session"]
    return {
        "key": "end_session_correct",
        "score": outputs["end_session"] == expected,
        "comment": f"expected {expected}, got {outputs['end_session']}",
    }


EVALUATORS = [format_valid, end_session_correct]
TARGETS = {"format_valid": 1.0, "end_session_correct": 0.95}
"""Minimum share of passing examples, from docs/prd.md §12."""
