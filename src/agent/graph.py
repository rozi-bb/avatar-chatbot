"""Wayan, the little host of Taman Gumitir, a fictional heritage hotel in Bali.

Every message is screened first: emergencies and requests for a person get a
fixed reply. Otherwise the model writes Wayan's reply from his persona, the
knowledge pack, and the current Bali time, and code checks it against the reply
contract before anyone hears it. docs/architecture.md shows the whole design.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cache
from typing import Any, NotRequired
from zoneinfo import ZoneInfo

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer

from agent import lines
from agent.prompts import SYSTEM_PROMPT, time_note
from agent.reply import check_reply
from agent.screen import MAX_GUEST_CHARS, Route, screen

MODEL_NAME = "deepseek-flash"

# A short think before answering: with thinking off, Wayan got "is the pool
# open now?" at 7 pm right only 5 times in 10; with low effort, 10 in 10, for
# about 0.25 s more before the first sentence (docs/architecture.md §8).
THINKING = {"thinking": {"type": "enabled"}}
THINKING_EFFORT = "low"

BALI = ZoneInfo("Asia/Makassar")


class State(MessagesState):
    """The conversation, where the latest message went, and whether it ended.

    Attributes:
        route: Where screen_message sent the guest's latest message.
        end_session: True when Wayan's latest reply said goodbye with [bye];
            the kiosk ends the session after speaking it.
    """

    route: NotRequired[Route]
    end_session: NotRequired[bool]


@dataclass
class Context:
    """Per-run settings, given by whoever starts the run.

    Attributes:
        channel: Where the run comes from: "studio", "kiosk", "eval", or "test".
            Recorded in the trace so runs can be filtered by source.
        now: The time Wayan believes it is. None means the current Bali time;
            evals pass a fixed time so their results repeat.
    """

    channel: str = "studio"
    now: datetime | str | None = None


def bali_now(ctx: Context) -> datetime:
    """Return the run's current time in Bali, from the context or the clock."""
    now = ctx.now
    if isinstance(now, str):  # Studio sends the context as JSON
        now = datetime.fromisoformat(now)
    if now is None:
        return datetime.now(BALI)
    return now.astimezone(BALI) if now.tzinfo else now.replace(tzinfo=BALI)


def run_metadata(runtime: Runtime[Context]) -> dict[str, Any]:
    """Return the trace metadata for a run: its session and its channel."""
    ctx = runtime.context or Context()
    info = runtime.execution_info
    return {"session_id": info.thread_id if info else None, "channel": ctx.channel}


@cache
def default_model() -> BaseChatModel:
    """Return the DeepSeek model, created on first use.

    Created lazily because ChatDeepSeek refuses to start without an API key,
    and unit tests run without one.
    """
    return ChatDeepSeek(
        model=MODEL_NAME,
        max_tokens=800,  # thinking counts too; check_reply limits what is said
        timeout=20,
        max_retries=1,
        reasoning_effort=THINKING_EFFORT,
        extra_body=THINKING,
    )


def build_graph(
    model: BaseChatModel | None = None,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph[State, Context, State, State]:
    """Build Wayan's graph.

    Args:
        model: Chat model for Wayan's replies. Defaults to DeepSeek; tests pass a fake.
        checkpointer: Only for running the graph outside `langgraph dev`, which
            stores threads itself.
    """

    async def wayan(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        """Reply to the guest as Wayan."""
        ctx = runtime.context or Context()
        # The time goes last, after everything that is the same for every guest.
        system = f"{SYSTEM_PROMPT}\n\n{time_note(bali_now(ctx))}"
        reply = await (model or default_model()).ainvoke(
            [SystemMessage(system), *state["messages"]],
            config={"metadata": run_metadata(runtime)},
        )
        return {"messages": [reply]}

    def screen_message(state: State) -> dict[str, Any]:
        """Cut the guest's message to size and pick its route, before any model call."""
        message = state["messages"][-1]
        update: dict[str, Any] = {"route": screen(message.text)}
        if isinstance(message, HumanMessage) and len(message.text) > MAX_GUEST_CHARS:
            cut = message.text[:MAX_GUEST_CHARS]
            update["messages"] = [message.model_copy(update={"content": cut})]
        return update

    def after_screen(state: State) -> str:
        return "wayan" if state.get("route", "normal") == "normal" else "fixed_reply"

    def fixed_reply(state: State) -> dict[str, Any]:
        """Answer an emergency or a request for a person with the fixed line."""
        line = lines.EMERGENCY if state.get("route") == "emergency" else lines.STAFF
        return {"messages": [AIMessage(line)], "end_session": False}

    def check(state: State) -> dict[str, Any]:
        """Hold Wayan's reply to the reply contract before it is spoken."""
        reply = state["messages"][-1]
        checked = check_reply(reply.text)
        # A guest who just asked something isn't leaving, whatever the model
        # thinks. Ending by mistake cuts them off; missing a goodbye costs
        # nothing, because the kiosk's idle timer ends the session anyway.
        guest = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        asked = guest is not None and "?" in guest.text
        # Same message ID, so add_messages replaces the raw reply: the thread
        # remembers exactly what Wayan says, without his thinking.
        kept = {
            k: v for k, v in reply.additional_kwargs.items() if k != "reasoning_content"
        }
        return {
            "messages": [
                reply.model_copy(
                    update={"content": checked.text, "additional_kwargs": kept}
                )
            ],
            "end_session": checked.end_session and not asked,
        }

    builder: StateGraph[State, Context, State, State] = StateGraph(
        State, context_schema=Context
    )
    builder.add_node(screen_message)
    builder.add_node(fixed_reply)
    builder.add_node(wayan)
    builder.add_node("check_reply", check)
    builder.add_edge(START, "screen_message")
    builder.add_conditional_edges(
        "screen_message", after_screen, ["wayan", "fixed_reply"]
    )
    builder.add_edge("fixed_reply", END)
    builder.add_edge("wayan", "check_reply")
    builder.add_edge("check_reply", END)
    return builder.compile(name="Wayan", checkpointer=checkpointer)


graph = build_graph()
