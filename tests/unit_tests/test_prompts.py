from datetime import datetime

import pytest
from langchain_core.messages import HumanMessage

from agent.graph import BALI, Context, bali_now, build_graph
from agent.prompts import SYSTEM_PROMPT, time_note
from unit_tests.fakes import PromptRecorder, fake_model


def test_both_knowledge_files_are_in_the_prompt() -> None:
    assert "HOTEL FACTS:" in SYSTEM_PROMPT and "CULTURE NOTES:" in SYSTEM_PROMPT
    assert "Pak Bos" in SYSTEM_PROMPT  # from knowledge/hotel.md
    assert "Nyepi" in SYSTEM_PROMPT  # from knowledge/bali-culture.md


def test_notes_for_editors_stay_out_of_the_prompt() -> None:
    assert "Fictional" not in SYSTEM_PROMPT
    assert "Status:" not in SYSTEM_PROMPT


def test_time_note_reads_like_a_clock() -> None:
    note = time_note(datetime(2026, 10, 21, 19, 0, tzinfo=BALI))

    assert (
        note
        == "Right now in Bali it is Wednesday, 21 October 2026, 7:00 pm (19:00, WITA)."
    )


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 10, 21, 19, 0, tzinfo=BALI),
        datetime.fromisoformat("2026-10-21T11:00:00+00:00"),
        "2026-10-21T19:00:00+08:00",
        datetime(2026, 10, 21, 19, 0),
    ],
)
def test_given_times_are_read_as_bali_time(now: datetime | str) -> None:
    assert bali_now(Context(now=now)) == datetime(2026, 10, 21, 19, 0, tzinfo=BALI)


def test_without_a_given_time_the_clock_is_bali_time() -> None:
    assert bali_now(Context()).utcoffset() == BALI.utcoffset(datetime(2026, 1, 1))


@pytest.mark.anyio
async def test_the_model_gets_the_given_time_last() -> None:
    recorder = PromptRecorder()
    await build_graph(fake_model("[smile] Hi!")).ainvoke(
        {"messages": [HumanMessage("What's on tonight?")]},
        {"callbacks": [recorder]},
        context=Context(now=datetime(2026, 10, 21, 19, 0, tzinfo=BALI)),
    )

    system = recorder.calls[0][0].text
    assert system.startswith(SYSTEM_PROMPT)
    assert system.endswith("Wednesday, 21 October 2026, 7:00 pm (19:00, WITA).")
