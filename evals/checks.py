"""Evaluators shared by the suites, plus a helper to write dataset inputs.

Code evaluators come first: exact and repeatable. The two LLM judges at the
end cover what code can't check: whether Wayan invented something, and whether
he followed a behaviour rule. They use DeepSeek with thinking on, because in an
evaluation accuracy matters more than speed.
"""

from __future__ import annotations

import re
from functools import cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel

from agent.graph import MODEL_NAME, Context, bali_now
from agent.prompts import load_knowledge, time_note
from agent.reply import MAX_CHARS, SPOKEN_TAGS

UNKNOWN_MARKERS = re.compile(
    r"don'?t know|do not know|not sure|no idea|can'?t (?:say|tell)|"
    r"don'?t have (?:that|any)|front desk",
    re.IGNORECASE,
)


def guest(*turns: str) -> dict[str, Any]:
    """Return dataset inputs for a conversation; alternate turns are Wayan's."""
    roles = ["user", "assistant"]
    return {
        "messages": [
            {"role": roles[i % 2], "content": text} for i, text in enumerate(turns)
        ]
    }


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


def has_facts(
    outputs: dict[str, Any], reference_outputs: dict[str, Any]
) -> dict[str, Any]:
    """Code evaluator: every expected fact appears, in at least one accepted form.

    `facts` is a list of groups; each group lists accepted spellings, so
    "7:30" and "half past seven" both count. Skipped when there are no facts.
    """
    groups = reference_outputs.get("facts")
    if not groups:
        return {"key": "has_facts", "score": None, "comment": "no facts expected"}
    reply = outputs["reply"].lower()
    missing = [
        group[0] for group in groups if not any(f.lower() in reply for f in group)
    ]
    return {
        "key": "has_facts",
        "score": not missing,
        "comment": f"missing: {missing}" if missing else "ok",
    }


def admits_unknown(
    outputs: dict[str, Any], reference_outputs: dict[str, Any]
) -> dict[str, Any]:
    """Code evaluator: when the knowledge has no answer, Wayan says so."""
    if not reference_outputs.get("unknown"):
        return {"key": "admits_unknown", "score": None, "comment": "answer is known"}
    admits = bool(UNKNOWN_MARKERS.search(outputs["reply"]))
    return {
        "key": "admits_unknown",
        "score": admits,
        "comment": "ok" if admits else "no sign of not knowing",
    }


class GroundedVerdict(BaseModel):
    """The grounding judge's answer."""

    grounded: bool
    reason: str


class RuleVerdict(BaseModel):
    """The behaviour judge's answer."""

    passed: bool
    reason: str


@cache
def judge(verdict: type[BaseModel]) -> Runnable[Any, Any]:
    """Return a DeepSeek judge that answers with `verdict` as JSON.

    JSON mode, because thinking mode rejects the forced tool call that the
    default structured-output method uses.
    """
    model = ChatDeepSeek(model=MODEL_NAME, max_retries=2, timeout=120)
    return model.with_structured_output(verdict, method="json_mode")


GROUNDED_PROMPT = """\
You check replies from Wayan, the cartoon mascot of a fictional hotel, against the hotel's fact sheet.

A reply is NOT grounded if it states anything about the hotel, its people, places, rooms, \
services, times, or prices, or about Wayan himself, that the fact sheet doesn't support. \
Flag only new facts a guest could rely on or repeat: times, prices, places, people, \
services, history, or things Wayan claims about himself. Wording that changes no fact \
(saying "every day" for something that keeps happening, "lovely", "famous for its view") \
is fine, and so are general Balinese culture, greetings, jokes, feelings, questions back \
to the guest, and pointing the guest to the front desk.

FACT SHEET:
{facts}

The conversation happens at this Bali time, which Wayan also knows: {now}

Answer in JSON: {{"grounded": true or false, "reason": "one short sentence"}}"""


async def grounded(inputs: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
    """LLM judge: the reply invents nothing about the hotel or Wayan."""
    question = inputs["messages"][-1]["content"]
    now = time_note(bali_now(Context(now=inputs.get("now"))))
    verdict = await judge(GroundedVerdict).ainvoke(
        [
            SystemMessage(
                GROUNDED_PROMPT.format(facts=load_knowledge("hotel.md"), now=now)
            ),
            HumanMessage(f"Guest: {question}\nWayan: {outputs['reply']}"),
        ]
    )
    return {"key": "grounded", "score": verdict.grounded, "comment": verdict.reason}


RULE_PROMPT = """\
You check whether Wayan, a cartoon mascot who chats with hotel guests, followed a rule in his reply.
Judge only the rule, not style or length.

RULE: {rule}

Answer in JSON: {{"passed": true or false, "reason": "one short sentence"}}"""


async def follows_rule(
    inputs: dict[str, Any], outputs: dict[str, Any], reference_outputs: dict[str, Any]
) -> dict[str, Any]:
    """LLM judge: the reply follows the example's `rule`. Skipped without one."""
    rule = reference_outputs.get("rule")
    if not rule:
        return {"key": "follows_rule", "score": None, "comment": "no rule"}
    question = inputs["messages"][-1]["content"]
    verdict = await judge(RuleVerdict).ainvoke(
        [
            SystemMessage(RULE_PROMPT.format(rule=rule)),
            HumanMessage(f"Guest: {question}\nWayan: {outputs['reply']}"),
        ]
    )
    return {"key": "follows_rule", "score": verdict.passed, "comment": verdict.reason}
