import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.pregel import Pregel

from agent import lines
from agent.graph import (
    MODEL_NAME,
    THINKING,
    THINKING_EFFORT,
    Context,
    build_graph,
    default_model,
    graph,
)
from agent.prompts import SYSTEM_PROMPT
from agent.screen import MAX_GUEST_CHARS
from unit_tests.fakes import PromptRecorder, fake_model


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
    assert sent[0].text.startswith(SYSTEM_PROMPT)
    assert isinstance(sent[-1], HumanMessage)
    assert [type(m) for m in result["messages"]] == [HumanMessage, AIMessage]


def test_deepseek_thinks_briefly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-tests")
    default_model.cache_clear()
    try:
        model = default_model()
    finally:
        default_model.cache_clear()

    assert isinstance(model, ChatDeepSeek)
    assert model.model_name == MODEL_NAME
    assert model.extra_body == THINKING
    assert model.reasoning_effort == THINKING_EFFORT == "low"


@pytest.mark.anyio
async def test_wayan_remembers_earlier_turns_in_one_session() -> None:
    recorder = PromptRecorder()
    wayan = build_graph(
        fake_model("[smile] I'm Wayan!", "[smile] You asked who I am."),
        checkpointer=InMemorySaver(),
    )
    session = {"configurable": {"thread_id": "guest-1"}, "callbacks": [recorder]}

    await wayan.ainvoke({"messages": [HumanMessage("Who are you?")]}, session)
    await wayan.ainvoke({"messages": [HumanMessage("What did I ask?")]}, session)

    second_call = recorder.calls[1]
    assert [type(m) for m in second_call] == [
        SystemMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]


@pytest.mark.anyio
async def test_next_guest_starts_with_an_empty_memory() -> None:
    recorder = PromptRecorder()
    wayan = build_graph(
        fake_model("[smile] I'm Wayan!", "[smile] Hello!"),
        checkpointer=InMemorySaver(),
    )

    await wayan.ainvoke(
        {"messages": [HumanMessage("Who are you?")]},
        {"configurable": {"thread_id": "guest-1"}},
    )
    await wayan.ainvoke(
        {"messages": [HumanMessage("Hi!")]},
        {"configurable": {"thread_id": "guest-2"}, "callbacks": [recorder]},
    )

    [call] = recorder.calls
    assert [type(m) for m in call] == [SystemMessage, HumanMessage]


@pytest.mark.anyio
async def test_model_call_is_tagged_with_session_and_channel() -> None:
    recorder = PromptRecorder()
    wayan = build_graph(fake_model("[smile] Hi!"), checkpointer=InMemorySaver())

    await wayan.ainvoke(
        {"messages": [HumanMessage("Hi!")]},
        {"configurable": {"thread_id": "guest-7"}, "callbacks": [recorder]},
        context=Context(channel="kiosk"),
    )

    [metadata] = recorder.metadata
    assert metadata["session_id"] == "guest-7"
    assert metadata["channel"] == "kiosk"


@pytest.mark.anyio
async def test_channel_defaults_to_studio() -> None:
    recorder = PromptRecorder()

    await build_graph(fake_model("[smile] Hi!")).ainvoke(
        {"messages": [HumanMessage("Hi!")]}, {"callbacks": [recorder]}
    )

    [metadata] = recorder.metadata
    assert metadata["channel"] == "studio"


@pytest.mark.anyio
async def test_the_stored_reply_is_the_checked_one() -> None:
    result = await build_graph(fake_model("Hi **friend** 😀! [wink]")).ainvoke(
        {"messages": [HumanMessage("Hi!")]}
    )

    assert [type(m) for m in result["messages"]] == [HumanMessage, AIMessage]
    assert result["messages"][-1].text == "[smile] Hi friend!"
    assert result["end_session"] is False


@pytest.mark.anyio
async def test_a_goodbye_ends_the_session() -> None:
    result = await build_graph(fake_model("[smile] Bye bye! [bye]")).ainvoke(
        {"messages": [HumanMessage("Bye Wayan!")]}
    )

    assert result["end_session"] is True
    assert "[bye]" not in result["messages"][-1].text


@pytest.mark.anyio
async def test_thinking_is_not_kept_in_the_thread() -> None:
    thinking = AIMessage(
        "[smile] Hi!", additional_kwargs={"reasoning_content": "Hmm..."}
    )
    model = GenericFakeChatModel(messages=iter([thinking]))

    result = await build_graph(model).ainvoke({"messages": [HumanMessage("Hi!")]})

    assert "reasoning_content" not in result["messages"][-1].additional_kwargs


@pytest.mark.anyio
async def test_an_emergency_gets_the_fixed_line_without_the_model() -> None:
    recorder = PromptRecorder()

    result = await build_graph(fake_model()).ainvoke(
        {"messages": [HumanMessage("Help! My daughter is lost!")]},
        {"callbacks": [recorder]},
    )

    assert recorder.calls == []
    assert result["route"] == "emergency"
    assert result["messages"][-1].text == lines.EMERGENCY
    assert result["end_session"] is False


@pytest.mark.anyio
async def test_a_request_for_a_person_gets_the_staff_line() -> None:
    result = await build_graph(fake_model()).ainvoke(
        {"messages": [HumanMessage("Can I talk to a real person?")]}
    )

    assert result["route"] == "staff"
    assert result["messages"][-1].text == lines.STAFF


@pytest.mark.anyio
async def test_a_long_message_is_cut_before_the_model_reads_it() -> None:
    recorder = PromptRecorder()

    result = await build_graph(fake_model("[smile] Wow, a long one!")).ainvoke(
        {"messages": [HumanMessage("tell me " * 100)]}, {"callbacks": [recorder]}
    )

    assert len(recorder.calls[0][-1].text) == MAX_GUEST_CHARS
    assert len(result["messages"]) == 2


@pytest.mark.anyio
async def test_a_help_tag_from_the_model_becomes_the_emergency_line() -> None:
    result = await build_graph(fake_model("[help]")).ainvoke(
        {"messages": [HumanMessage("My grandpa collapsed near the pool")]}
    )

    assert result["route"] == "normal"
    assert result["messages"][-1].text == lines.EMERGENCY


@pytest.mark.anyio
async def test_a_guest_who_asks_something_is_not_sent_away() -> None:
    result = await build_graph(
        fake_model("[smile] It's 88 years old! Safe travels! [bye]")
    ).ainvoke(
        {"messages": [HumanMessage("I'm leaving tomorrow. How old is the tree?")]}
    )

    assert result["end_session"] is False
    assert "[bye]" not in result["messages"][-1].text
