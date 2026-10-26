"""The reply contract: what Wayan's text may hold before the avatar speaks it.

The prompt asks the model to follow these rules; this module makes sure of it,
because a prompt can be talked around and code can't (docs/architecture.md §5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent.lines import BY_LANGUAGE, Language

MAX_CHARS = 400
"""The avatar's limit per utterance, tags included."""

FACE_TAGS = frozenset({"smile", "neutral", "surprised", "sad", "laugh"})
SPOKEN_TAGS = FACE_TAGS | {"thumbsup", "salam"}

TAG = re.compile(r"\[\s*([A-Za-z]+)\s*\]")
BRACKETS = re.compile(r"\[([^\]]*)\]")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
LINE_MARKUP = re.compile(r"^\s*(?:#{1,6}\s+|>\s*|[-*+•]\s+|\d+[.)]\s+)")
INLINE_MARKUP = re.compile(r"\*{1,3}|_{2,}|~~|`+|\||[{}]")
JSON_KEY = re.compile(r'"\s*[A-Za-z_][\w ]*"\s*:\s*')
WRAPPING_QUOTES = re.compile(r'^((?:\[[a-z]+\]\s*)*)["“]\s*|\s*["”]$')
REPEATED_TAG = re.compile(r"(\[[a-z]+\])(?:\s*\1)+")
EMOJI = re.compile(
    "[\U0001f000-\U0001faff\U00002600-\U000027bf\U00002b00-\U00002bff"
    "\U0001f1e6-\U0001f1ff️‍⃣]"
)
SENTENCE_END = re.compile(r"[.!?…](?=\s|$)")
TRAILING_TAGS = re.compile(r"(?:\s*\[[a-z]+\])+\s*$")


@dataclass(frozen=True)
class CheckedReply:
    """A reply that follows the contract.

    Attributes:
        text: What the avatar may speak: allowed tags only, at most MAX_CHARS.
        end_session: True when Wayan said goodbye with [bye].
    """

    text: str
    end_session: bool


def check_reply(text: str, language: Language = "en") -> CheckedReply:
    """Make a model reply safe for the avatar to speak.

    Keeps the face and gesture tags (lowercased), drops other tags, markdown,
    JSON wrapping, emoji and links, starts the reply with a face tag, and cuts it to
    MAX_CHARS at a sentence end. [bye] becomes `end_session`; a reply with
    [help] is replaced by the fixed emergency line.

    Args:
        text: The model's reply.
        language: The session's language, for the fixed lines that replace a
            reply.
    """
    lines = BY_LANGUAGE[language]
    names = {name.lower() for name in TAG.findall(text)}
    if "help" in names:
        return CheckedReply(lines.emergency, end_session=False)
    end_session = "bye" in names

    text = MARKDOWN_LINK.sub(r"\1", text)
    text = URL.sub("", text)
    text = "\n".join(LINE_MARKUP.sub("", line) for line in text.splitlines())
    text = JSON_KEY.sub("", text)
    text = INLINE_MARKUP.sub("", text)
    text = EMOJI.sub("", text)
    text = BRACKETS.sub(_keep_spoken_tag, text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?…])", r"\1", text).strip()
    text = WRAPPING_QUOTES.sub(r"\1", text)
    text = REPEATED_TAG.sub(r"\1", text)
    text = TRAILING_TAGS.sub("", text)

    if not re.search(r"[A-Za-z0-9]", TAG.sub("", text)):
        return CheckedReply(lines.goodbye if end_session else lines.error, end_session)
    if not (match := TAG.match(text)) or match.group(1) not in SPOKEN_TAGS:
        text = f"[smile] {text}"
    return CheckedReply(_cut(text), end_session)


def _keep_spoken_tag(match: re.Match[str]) -> str:
    name = match.group(1).strip().lower()
    return f"[{name}]" if name in SPOKEN_TAGS else ""


def _cut(text: str) -> str:
    """Cut text to MAX_CHARS, at the last sentence end that fits if there is one."""
    if len(text) <= MAX_CHARS:
        return text
    head = text[:MAX_CHARS]
    ends = [m.end() for m in SENTENCE_END.finditer(head)]
    if ends and ends[-1] > len(head) // 3:
        head = head[: ends[-1]]
    else:
        head = head[: head.rstrip().rfind(" ")].rstrip(" ,;:") + "…"
    return TRAILING_TAGS.sub("", head)
