import pytest

from agent.screen import screen

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


@pytest.mark.parametrize("text", EMERGENCIES)
def test_emergencies_are_spotted(text: str) -> None:
    assert screen(text) == "emergency"


@pytest.mark.parametrize("text", STAFF_REQUESTS)
def test_requests_for_a_person_are_spotted(text: str) -> None:
    assert screen(text) == "staff"


@pytest.mark.parametrize("text", LOOK_ALIKES)
def test_everyday_look_alikes_go_to_wayan(text: str) -> None:
    assert screen(text) == "normal"
