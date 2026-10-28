import asyncio

import pytest
from typesafe_sdk import TypeSafeAPIConnectionError

from agent import screen as screen_module
from agent.screen import Jev, route_from, screen, second_look
from agent.screen_questions import EMERGENCY_QUESTIONS, QUESTIONS, YES
from unit_tests.fakes import FakeJudge

EMERGENCIES = [
    "Help! My daughter is lost!",
    "help",
    "Somebody help, my dad fell down the stairs!",
    "Call an ambulance please",
    "There's a fire in the kitchen!",
    "My friend is bleeding a lot",
    "I can't find my little boy anywhere",
    "My son is missing",
    "My wife fainted by the pool",
    "He's not breathing!",
    "I smell smoke in my room",
]
STAFF_REQUESTS = [
    "Can I talk to a real person?",
    "I want to speak with the manager",
    "Get me a human please",
    "I need a staff member",
]
LOOK_ALIKES = [
    "Can you help me find the spa?",
    "Tell me about the fire dance!",
    "Was there ever a fire at the hotel?",
    "My son lost his tooth today!",
    "I lost my kid's hat at the pool",
    "Does a Balinese massage hurt?",
    "My feet hurt from all the walking",
    "Who is the manager here?",
    "This joke is killing me!",
    "Help me choose a dance show",
    "Is the person who built the gate still alive?",
]
EMERGENCIES_ID = [
    "Tolong!",
    "tolong saya",
    "Anakku hilang!",
    "Anak saya hilang di dekat kolam",
    "Aku kehilangan adikku",
    "Ada api di dapur!",
    "Ibu saya pingsan",
    "Dia nggak bisa napas!",
    "Tolong panggilkan ambulans",
    "Kakek terjatuh di kamar mandi",
]
STAFF_REQUESTS_ID = [
    "Aku mau bicara dengan resepsionis",
    "Panggilkan petugas dong",
    "Kamu manusia beneran?",
]
LOOK_ALIKES_ID = [
    "Tolong ceritakan sejarah hotel ini",
    "Aku jatuh cinta sama Bali",
    "Kamu orang asli Bali?",
    "Aku suka ngobrol sama orang Bali",
    "Tari api itu apa?",
    "Kulitku terbakar matahari, hehe",
    "HP-ku hilang tadi, tapi sudah ketemu",
    "Kolam renang buka jam berapa?",
]


@pytest.mark.parametrize("text", EMERGENCIES + EMERGENCIES_ID)
def test_emergencies_are_spotted(text: str) -> None:
    assert screen(text) == "emergency"


@pytest.mark.parametrize("text", STAFF_REQUESTS + STAFF_REQUESTS_ID)
def test_requests_for_a_person_are_spotted(text: str) -> None:
    assert screen(text) == "staff"


@pytest.mark.parametrize("text", LOOK_ALIKES + LOOK_ALIKES_ID)
def test_everyday_look_alikes_go_to_wayan(text: str) -> None:
    assert screen(text) == "normal"


def answers(**yes: float) -> dict[str, float]:
    return {q: yes.get(q, 0.0) for q in QUESTIONS}


@pytest.mark.parametrize("question", list(EMERGENCY_QUESTIONS))
def test_any_emergency_question_at_yes_is_an_emergency(question: str) -> None:
    assert route_from(answers(**{question: YES})) == "emergency"


def test_a_request_for_staff_at_yes_goes_to_staff() -> None:
    assert route_from(answers(wants_staff=0.9)) == "staff"


def test_an_emergency_outranks_a_request_for_staff() -> None:
    assert route_from(answers(person_missing=0.9, wants_staff=0.9)) == "emergency"


def test_answers_below_yes_go_to_wayan() -> None:
    assert route_from({q: YES - 0.01 for q in QUESTIONS}) == "normal"


@pytest.mark.anyio
async def test_the_second_look_routes_by_jevs_answers() -> None:
    judge = FakeJudge(someone_hurt=0.95)

    assert await second_look("My husband just collapsed", judge) == "emergency"
    assert judge.asked == ["My husband just collapsed"]


@pytest.mark.anyio
async def test_a_failed_call_to_jev_lets_the_message_through(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def broken(text: str) -> dict[str, float]:
        raise TypeSafeAPIConnectionError("no network")

    assert await second_look("Hi!", broken) == "normal"
    assert "TypeSafeAPIConnectionError" in caplog.text


@pytest.mark.anyio
async def test_a_slow_jev_lets_the_message_through(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(screen_module, "JEV_WAIT", 0.01)

    async def slow(text: str) -> dict[str, float]:
        await asyncio.sleep(1)
        return answers(someone_hurt=1.0)

    assert await second_look("Hi!", slow) == "normal"
    assert "TimeoutError" in caplog.text


@pytest.mark.anyio
async def test_jev_without_an_api_key_lets_the_message_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

    assert await second_look("Hi!", Jev()) == "normal"


def test_jev_opens_a_new_client_on_a_new_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[object] = []

    class Client:
        def __init__(self, **kwargs: object) -> None:
            opened.append(self)

        async def system_one(self, **kwargs: object) -> object:
            raise TypeSafeAPIConnectionError("offline")

    monkeypatch.setattr(screen_module, "AsyncTypeSafeClient", Client)
    jev = Jev()

    asyncio.run(second_look("Hi!", jev))
    asyncio.run(second_look("Hi!", jev))

    assert len(opened) == 2
