from typing import Any

import pytest
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.pregel import Pregel

from agent.graph import MODEL_NAME, THINKING_OFF, build_graph, default_model, graph
from agent.prompts import SYSTEM_PROMPT


class PromptRecorder(AsyncCallbackHandler):
    """Keeps the messages that each chat model call received."""

    def __init__(self) -> None:
        self.calls: list[list[BaseMessage]] = []

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        self.calls.extend(messages)


def fake_model(*replies: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(r) for r in replies]))


def test_graph_builds_without_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    assert isinstance(build_graph(), Pregel)
    assert isinstance(graph, Pregel)


@pytest.mark.anyio
async def test_wayan_gets_his_persona_and_the_conversation() -> None:
    recorder = PromptRecorder()

    result = await build_graph(fake_model("[smile] Om Swastiastu!")).ainvoke(
        {"messages": [HumanMessage("Hi!")]}, config={"callbacks": [recorder]}
    )

    [sent] = recorder.calls
    assert isinstance(sent[0], SystemMessage)
    assert sent[0].content == SYSTEM_PROMPT
    assert isinstance(sent[-1], HumanMessage)
    assert [type(m) for m in result["messages"]] == [HumanMessage, AIMessage]


def test_deepseek_runs_with_thinking_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-tests")
    default_model.cache_clear()
    try:
        model = default_model()
    finally:
        default_model.cache_clear()

    assert isinstance(model, ChatDeepSeek)
    assert model.model_name == MODEL_NAME
    assert model.extra_body == THINKING_OFF
