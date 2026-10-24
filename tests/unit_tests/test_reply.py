import re

import pytest

from agent import lines
from agent.reply import MAX_CHARS, SPOKEN_TAGS, check_reply


def tags(text: str) -> list[str]:
    return re.findall(r"\[([^\]]*)\]", text)


def test_a_good_reply_stays_as_it_is() -> None:
    reply = "[smile] Hi there! [surprised] Our tree is from 1938."

    assert check_reply(reply).text == reply
    assert check_reply(reply).end_session is False


def test_tags_are_lowercased_and_unknown_tags_dropped() -> None:
    result = check_reply("[Smile] Hi! [wink] I'm Wayan. [senyum] [THUMBSUP] Great!")

    assert tags(result.text) == ["smile", "thumbsup"]
    assert "  " not in result.text


def test_a_reply_without_a_leading_face_tag_gets_a_smile() -> None:
    assert check_reply("Hello! [laugh] Ha.").text.startswith("[smile] Hello!")


def test_markdown_is_removed() -> None:
    result = check_reply(
        "[smile] **Wow!** Here is what we have:\n- a pool\n* a spa\n1. yoga\n# Fun\n`code` | table |"
    )

    assert not re.search(r"[*#`|]|^- |\n", result.text)
    assert "a pool" in result.text and "yoga" in result.text


def test_json_wrapping_is_removed() -> None:
    result = check_reply('{"answer": "[smile] Two plus two is four! Want another?"}')

    assert result.text == "[smile] Two plus two is four! Want another?"


def test_links_are_removed() -> None:
    result = check_reply(
        "[smile] See https://example.com or www.example.com, or [our site](https://x.io)!"
    )

    assert "http" not in result.text and "www." not in result.text
    assert "our site" in result.text


def test_emoji_are_removed() -> None:
    result = check_reply("[smile] Hi friend 😀🌺👍🏽! I love ☀️ days.")

    assert result.text == "[smile] Hi friend! I love days."


@pytest.mark.parametrize("sentence", ["This is a sentence about Bali. ", "word "])
def test_long_replies_are_cut_to_the_limit(sentence: str) -> None:
    result = check_reply("[smile] " + sentence * 100)

    assert len("[smile] " + sentence * 100) > MAX_CHARS

    assert len(result.text) <= MAX_CHARS
    assert result.text.endswith((".", "…"))


def test_bye_ends_the_session_and_is_not_spoken() -> None:
    result = check_reply("[smile] Bye bye! Come back soon. [bye]")

    assert result.end_session is True
    assert "bye]" not in result.text
    assert result.text == "[smile] Bye bye! Come back soon."


def test_a_bare_bye_still_says_goodbye() -> None:
    assert check_reply("[bye]") == check_reply(" [BYE] ")
    assert check_reply("[bye]").text == lines.GOODBYE
    assert check_reply("[bye]").end_session is True


def test_help_is_replaced_by_the_fixed_emergency_line() -> None:
    result = check_reply("[help] Oh no, let me think about that...")

    assert result.text == lines.EMERGENCY
    assert result.end_session is False


def test_an_empty_reply_becomes_the_error_line() -> None:
    assert check_reply("").text == lines.ERROR
    assert check_reply("[smile] 😀").text == lines.ERROR


@pytest.mark.parametrize("line", lines.ALL)
def test_fixed_lines_follow_the_contract(line: str) -> None:
    assert check_reply(line).text == line
    assert set(tags(line)) <= SPOKEN_TAGS
