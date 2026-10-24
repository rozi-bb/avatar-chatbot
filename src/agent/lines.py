"""Wayan's fixed lines (docs/prd.md §11).

Said without a model call: instantly, the same every time, and easy to test.
Every line keeps the reply contract in agent.reply.
"""

GREETINGS = (
    "[smile] Om Swastiastu! I'm Wayan, the little host of Taman Gumitir. "
    "Ask me anything about our hotel or Bali!",
    "[smile] Hello hello! I'm Wayan. Want to hear a story about this hotel, "
    "or a fun fact about Bali?",
    "[thumbsup] Welcome to Taman Gumitir! I'm Wayan, your little host. "
    "What would you like to know?",
)
"""Said when a guest presses Start; one is picked at random."""

STILL_THERE = "[smile] Are you still there? I'm right here if you want to chat."
IDLE_GOODBYE = "[smile] Okay, I'll be right here when you need me. Bye bye!"
EMERGENCY = (
    "[neutral] This sounds important! Please go to the front desk in the lobby "
    "right now, or ask any staff member. If someone is in danger, call 112."
)
STAFF = (
    "[smile] Sure! My friends at the front desk are here day and night, right here "
    "in the lobby. They'll be happy to help."
)
ERROR = (
    "[sad] Oops, my brain got a bit tangled. Could you say that again? "
    "If it keeps happening, the front desk can help."
)
TURN_LIMIT = (
    "[smile] Wow, we talked so much! I need to rest my voice now. "
    "Press Start anytime to chat again. Bye bye!"
)
RESTING = (
    "[smile] I'm resting my voice for today. My friends at the front desk can help you!"
)
GOODBYE = "[smile] Bye bye!"
"""Used when a reply holds nothing but [bye]."""

ALL = (
    *GREETINGS,
    STILL_THERE,
    IDLE_GOODBYE,
    EMERGENCY,
    STAFF,
    ERROR,
    TURN_LIMIT,
    RESTING,
    GOODBYE,
)
