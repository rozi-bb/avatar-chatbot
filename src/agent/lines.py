"""Wayan's fixed lines (docs/prd.md §11), in each language he speaks.

Said without a model call: instantly, the same every time, and easy to test.
Every line keeps the reply contract in agent.reply. Tags stay in English in
every language: they drive the avatar, and are never read aloud.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "id"]
"""The language a session runs in, picked on the kiosk before Start."""


@dataclass(frozen=True)
class Lines:
    """One language's fixed lines.

    Attributes:
        greetings: Said when a guest presses Start; one is picked at random.
            Each opens with [salam] Om Swastiastu, the same welcome every time.
        fillers: Said by the kiosk page when a reply takes more than 2 s, so the
            guest isn't left in silence; one is picked at random. Never stored.
        still_there: Said after 45 s of quiet.
        idle_goodbye: Said after 60 s of quiet; ends the session.
        emergency: The reply to an emergency.
        staff: The reply to a request for a person.
        error: Said when the model fails or its reply is empty.
        turn_limit: Said instead of a reply once the session reached its turn limit.
        resting: Said instead of a reply once the day's budget is used up.
        goodbye: Used when a reply holds nothing but [bye].
    """

    greetings: tuple[str, ...]
    fillers: tuple[str, ...]
    still_there: str
    idle_goodbye: str
    emergency: str
    staff: str
    error: str
    turn_limit: str
    resting: str
    goodbye: str

    @property
    def all(self) -> tuple[str, ...]:
        """Every line, for tests that check them all."""
        return (
            *self.greetings,
            *self.fillers,
            self.still_there,
            self.idle_goodbye,
            self.emergency,
            self.staff,
            self.error,
            self.turn_limit,
            self.resting,
            self.goodbye,
        )


ENGLISH = Lines(
    greetings=(
        "[salam] Om Swastiastu! I'm Wayan, the little host of Taman Gumitir. "
        "Ask me anything about our hotel or Bali!",
        "[salam] Om Swastiastu! I'm Wayan. Want to hear a story about this hotel, "
        "or a fun fact about Bali?",
        "[salam] Om Swastiastu, welcome to Taman Gumitir! I'm Wayan, your little "
        "host. What would you like to know?",
    ),
    fillers=(
        "[smile] Hmm, wait a second, let me think...",
        "[smile] Ooh, hold on, I'm remembering...",
        "[smile] Hmm, just a moment...",
    ),
    still_there="[smile] Are you still there? I'm right here if you want to chat.",
    idle_goodbye="[smile] Okay, I'll be right here when you need me. Bye bye!",
    emergency=(
        "[neutral] This sounds important! Please go to the front desk in the lobby "
        "right now, or ask any staff member. If someone is in danger, call 112."
    ),
    staff=(
        "[smile] Sure! My friends at the front desk are here day and night, right "
        "here in the lobby. They'll be happy to help."
    ),
    error=(
        "[sad] Oops, my brain got a bit tangled. Could you say that again? "
        "If it keeps happening, the front desk can help."
    ),
    turn_limit=(
        "[smile] Wow, we talked so much! I need to rest my voice now. "
        "Press Start anytime to chat again. Bye bye!"
    ),
    resting=(
        "[smile] I'm resting my voice for today. "
        "My friends at the front desk can help you!"
    ),
    goodbye="[smile] Bye bye!",
)

INDONESIAN = Lines(
    greetings=(
        "[salam] Om Swastiastu! Aku Wayan, tuan rumah cilik Taman Gumitir. "
        "Tanya apa aja soal hotel kami atau Bali, ya!",
        "[salam] Om Swastiastu! Aku Wayan. Mau dengar cerita tentang hotel ini, "
        "atau fakta seru soal Bali?",
        "[salam] Om Swastiastu, selamat datang di Taman Gumitir! Aku Wayan, tuan "
        "rumah cilikmu. Mau tahu apa nih?",
    ),
    fillers=(
        "[smile] Hmm, sebentar ya, aku ingat-ingat dulu...",
        "[smile] Ooh, tunggu ya, aku pikir dulu...",
        "[smile] Hmm, sebentar...",
    ),
    still_there="[smile] Masih di situ? Aku di sini kok kalau mau ngobrol lagi.",
    idle_goodbye="[smile] Oke, aku tunggu di sini ya kalau butuh aku. Dadah!",
    emergency=(
        "[neutral] Ini kedengarannya penting! Tolong segera ke meja resepsionis di "
        "lobi, atau minta tolong staf mana saja. Kalau ada yang dalam bahaya, "
        "telepon 112."
    ),
    staff=(
        "[smile] Boleh! Teman-temanku di meja resepsionis ada siang dan malam, di "
        "lobi sini. Mereka pasti senang membantu."
    ),
    error=(
        "[sad] Aduh, otakku lagi kusut nih. Bisa diulang lagi? "
        "Kalau masih begini terus, teman-teman di resepsionis bisa bantu."
    ),
    turn_limit=(
        "[smile] Wah, kita sudah ngobrol banyak banget! Suaraku perlu istirahat "
        "dulu. Tekan Mulai kapan saja buat ngobrol lagi. Dadah!"
    ),
    resting=(
        "[smile] Hari ini suaraku lagi istirahat. "
        "Teman-temanku di meja resepsionis bisa bantu kamu!"
    ),
    goodbye="[smile] Dadah!",
)

BY_LANGUAGE: dict[Language, Lines] = {"en": ENGLISH, "id": INDONESIAN}
