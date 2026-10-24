"""Wayan, the little host of Taman Gumitir, a fictional heritage hotel in Bali.

Baseline graph (build step 8): one model call with Wayan's persona. The
milestones in docs/roadmap.md add the reply contract, the knowledge pack, and
the safety route; docs/architecture.md shows where it is heading.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer

from agent.prompts import SYSTEM_PROMPT

MODEL_NAME = "deepseek-flash"

# Thinking is on by default for deepseek-flash and delays the first word by
# seconds, which a voice conversation can't afford (docs/architecture.md §8).
THINKING_OFF = {"thinking": {"type": "disabled"}}


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
) -> CompiledStateGraph[MessagesState, Context, MessagesState, MessagesState]:
    """Build Wayan's graph.

    Args:
        model: Chat model for Wayan's replies. Defaults to DeepSeek; tests pass a fake.
        checkpointer: Only for running the graph outside `langgraph dev`, which
            stores threads itself.
    """

    async def wayan(state: MessagesState, runtime: Runtime[Context]) -> dict[str, Any]:
        """Reply to the guest as Wayan."""
        reply = await (model or default_model()).ainvoke(
            [SystemMessage(SYSTEM_PROMPT), *state["messages"]],
            config={"metadata": run_metadata(runtime)},
        )
        return {"messages": [reply]}

    builder: StateGraph[MessagesState, Context, MessagesState, MessagesState] = (
        StateGraph(MessagesState, context_schema=Context)
    )
    builder.add_node(wayan)
    builder.add_edge(START, "wayan")
    builder.add_edge("wayan", END)
    return builder.compile(name="Wayan", checkpointer=checkpointer)


graph = build_graph()
