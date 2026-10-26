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
