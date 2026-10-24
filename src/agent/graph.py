"""Wayan, the little host of Taman Gumitir, a fictional heritage hotel in Bali.

The model writes Wayan's reply, then code checks it against the reply
contract before anyone hears it. The milestones in docs/roadmap.md add the
knowledge pack and the safety route next; docs/architecture.md shows where it
is heading.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any, NotRequired

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer

from agent.prompts import SYSTEM_PROMPT
from agent.reply import check_reply

MODEL_NAME = "deepseek-flash"

# Thinking is on by default for deepseek-flash and delays the first word by
# seconds, which a voice conversation can't afford (docs/architecture.md §8).
THINKING_OFF = {"thinking": {"type": "disabled"}}


class State(MessagesState):
    """The conversation, plus whether Wayan just ended it.

    Attributes:
        end_session: True when Wayan's latest reply said goodbye with [bye];
            the kiosk ends the session after speaking it.
    """

    end_session: NotRequired[bool]


@dataclass
class Context:
    """Per-run settings, given by whoever starts the run.

    Attributes:
        channel: Where the run comes from: "studio", "kiosk", "eval", or "test".
            Recorded in the trace so runs can be filtered by source.
    """

    channel: str = "studio"


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
        max_tokens=200,
        timeout=20,
        max_retries=1,
        extra_body=THINKING_OFF,
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
        reply = await (model or default_model()).ainvoke(
            [SystemMessage(SYSTEM_PROMPT), *state["messages"]],
            config={"metadata": run_metadata(runtime)},
        )
        return {"messages": [reply]}

    def check(state: State) -> dict[str, Any]:
        """Hold Wayan's reply to the reply contract before it is spoken."""
        reply = state["messages"][-1]
        checked = check_reply(reply.text)
        # Same message ID, so add_messages replaces the raw reply: the thread
        # remembers exactly what Wayan says.
        return {
            "messages": [reply.model_copy(update={"content": checked.text})],
            "end_session": checked.end_session,
        }

    builder: StateGraph[State, Context, State, State] = StateGraph(
        State, context_schema=Context
    )
    builder.add_node(wayan)
    builder.add_node("check_reply", check)
    builder.add_edge(START, "wayan")
    builder.add_edge("wayan", "check_reply")
    builder.add_edge("check_reply", END)
    return builder.compile(name="Wayan", checkpointer=checkpointer)


graph = build_graph()
