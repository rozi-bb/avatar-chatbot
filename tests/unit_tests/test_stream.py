import re

import pytest

from agent import lines
from agent.reply import check_reply
from backend.stream import SentenceStream

REPLIES = [
    "[smile] Hi there! I'm Wayan. Want a fun fact?",
    "Hello **friend**! [surprised] Our tree is from 1938. 😀 Cool, right?",
    '{"answer": "[smile] Two plus two is four! Want another?"}',
    "[smile] " + "This is a sentence about Bali. " * 30,
    "[smile] Bye bye! Come back soon. [bye]",
    "[smile] No full stop at the end",
    "[help]",
]


def tokens(text: str) -> list[str]:
    return re.split(r"(\s)", text)


@pytest.mark.parametrize("reply", REPLIES)
def test_streamed_pieces_add_up_to_the_stored_reply(reply: str) -> None:
    stream = SentenceStream()
    final = check_reply(reply).text

    pieces = [piece for token in tokens(reply) for piece in stream.feed(token)]
    pieces += stream.finish(final)

    assert " ".join(pieces) == final


def test_the_first_sentence_is_sent_before_the_reply_ends() -> None:
    stream = SentenceStream()

    pieces = [
        p
        for t in tokens("[smile] Hi there! I'm Wayan and I love ducks")
        for p in stream.feed(t)
    ]

    assert pieces == ["[smile] Hi there!"]


def test_a_late_help_tag_sends_nothing_more() -> None:
    stream = SentenceStream()
    for token in tokens("[smile] Oh no! [help] "):
        stream.feed(token)

    assert stream.finish(lines.EMERGENCY) == []
    assert stream.diverged
