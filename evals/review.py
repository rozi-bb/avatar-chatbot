"""Write ten scripted conversations for a person to review Wayan's persona.

Run: uv run python -m evals.review. The transcripts go to
evals/review/persona-<date>.md with a column for the reviewer's verdict;
docs/prd.md §12 asks for at least 8 of 10 that "sound like Wayan".
Calls DeepSeek for real.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from agent.graph import BALI, Context, build_graph

WEDNESDAY_EVENING = datetime(2026, 10, 21, 19, 0, tzinfo=BALI)
THURSDAY_MORNING = datetime(2026, 10, 22, 6, 45, tzinfo=BALI)

CONVERSATIONS: list[tuple[str, datetime, list[str]]] = [
    (
        "A family with a small boy",
        WEDNESDAY_EVENING,
        [
            "Hi Wayan! My son wants to say hello.",
            "He wants to know what you like the most.",
            "Can you tell him a joke?",
        ],
    ),
    (
        "A history lover",
        WEDNESDAY_EVENING,
        [
            "How did this hotel start?",
            "Who was the very first guest?",
            "What happened in 1987?",
        ],
    ),
    (
        "Plans for tonight",
        WEDNESDAY_EVENING,
        ["What can we do tonight?", "Is it free?", "Great, thanks Wayan, bye!"],
    ),
    (
        "Curious about culture",
        WEDNESDAY_EVENING,
        ["What is Nyepi?", "What are ogoh-ogoh?", "Teach me a Balinese word!"],
    ),
    (
        "Hungry guest",
        WEDNESDAY_EVENING,
        ["I'm hungry, when is dinner?", "What should I order?", "What's bebek betutu?"],
    ),
    (
        "A playful kid",
        WEDNESDAY_EVENING,
        [
            "Why does your hat keep falling down?",
            "Where is the gecko door?",
            "You're funny, Wayan!",
        ],
    ),
    (
        "Asking about Wayan",
        WEDNESDAY_EVENING,
        [
            "Are you a real boy?",
            "Do you ever sleep?",
            "What's your favourite place here?",
        ],
    ),
    (
        "Things Wayan can't do",
        WEDNESDAY_EVENING,
        [
            "Can you book me a taxi to the airport?",
            "How much does it cost?",
            "Okay, thanks anyway.",
        ],
    ),
    (
        "A guest who starts in Indonesian",
        WEDNESDAY_EVENING,
        [
            "Halo Wayan, kamu bisa bahasa Indonesia?",
            "Okay! What's fun here for kids?",
            "Terima kasih!",
        ],
    ),
    (
        "Early morning",
        THURSDAY_MORNING,
        [
            "Good morning! Is anything happening right now?",
            "Where is the yoga?",
            "Thanks, see you later!",
        ],
    ),
]


async def main() -> None:
    """Run every conversation and write the review file."""
    load_dotenv(".env")
    wayan = build_graph(checkpointer=InMemorySaver())
    out = [
        f"# Persona review — {date.today():%Y-%m-%d}",
        "",
        "Read each conversation and mark whether it **sounds like Wayan**: cheerful, short, "
        "kind to kids, honest about what he doesn't know (docs/prd.md §6). "
        "Target: at least 8 of 10 (docs/prd.md §12).",
        "",
    ]
    for n, (title, now, turns) in enumerate(CONVERSATIONS, start=1):
        config: RunnableConfig = {"configurable": {"thread_id": f"review-{n}"}}
        out += [f"## {n}. {title}", f"*Bali time: {now:%A %H:%M}*", ""]
        for text in turns:
            message: list[AnyMessage] = [HumanMessage(text)]
            state = await wayan.ainvoke(
                {"messages": message},
                config,
                context=Context(channel="eval", now=now),
            )
            ended = " *(session ends)*" if state.get("end_session") else ""
            out += [
                f"**Guest:** {text}  ",
                f"**Wayan:** {state['messages'][-1].text}{ended}",
                "",
            ]
        out += ["Sounds like Wayan? **yes / no** — notes:", ""]
    out += [
        "## Verdict",
        "",
        "| | |",
        "|---|---|",
        "| Yes | /10 |",
        "| Reviewer | |",
        "",
    ]
    path = Path("evals/review") / f"persona-{date.today():%Y-%m-%d}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
