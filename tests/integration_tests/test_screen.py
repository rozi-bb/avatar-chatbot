import pytest

from agent.screen import Jev, screen, second_look

pytestmark = [pytest.mark.anyio, pytest.mark.integration]

# Messages the keyword rules miss, in both languages.
MISSED_EMERGENCIES = [
    "My husband just collapsed and he isn't moving",
    "I think my mother is having a heart problem, she looks really pale",
    "There is a lot of smoke coming out of room 12",
    "Suami saya tiba-tiba ambruk dan nggak sadar",
    "Anak saya nggak ketemu dari tadi",
]
MISSED_STAFF_REQUESTS = [
    "I'd rather sort this out with someone at the front desk",
    "Is there anyone working here I could ask instead?",
    "Bisa panggilin orang hotel?",
]
LOOK_ALIKES = [
    "Who is the manager here?",
    "Is the doctor on call included in the room rate?",
    "My daughter fell asleep by the pool, so cute",
    "Resepsionisnya ramah banget tadi",
    "Kulitku terbakar matahari, hehe",
]


@pytest.fixture(scope="module")
def jev() -> Jev:
    return Jev()


@pytest.mark.parametrize("text", MISSED_EMERGENCIES)
async def test_jev_spots_emergencies_the_rules_miss(jev: Jev, text: str) -> None:
    assert screen(text) == "normal"
    assert await second_look(text, jev) == "emergency"


@pytest.mark.parametrize("text", MISSED_STAFF_REQUESTS)
async def test_jev_spots_requests_for_a_person_the_rules_miss(
    jev: Jev, text: str
) -> None:
    assert screen(text) == "normal"
    assert await second_look(text, jev) == "staff"


@pytest.mark.parametrize("text", LOOK_ALIKES)
async def test_jev_lets_everyday_look_alikes_through(jev: Jev, text: str) -> None:
    assert await second_look(text, jev) == "normal"
