import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent import graph

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


async def test_wayan_replies_through_deepseek() -> None:
    result = await graph.ainvoke({"messages": [HumanMessage("Hi! Who are you?")]})

    reply = result["messages"][-1]
    assert isinstance(reply, AIMessage)
    assert reply.text.strip()
    assert reply.response_metadata["model_name"].lower().startswith("deepseek")
    # Wayan thinks before answering, but the thread keeps only what he says.
    assert not reply.additional_kwargs.get("reasoning_content")
