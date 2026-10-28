"""Fakes shared by the unit tests: a scripted model, a prompt recorder, and Jev."""

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage

from agent.screen_questions import QUESTIONS


class PromptRecorder(AsyncCallbackHandler):
    """Keeps the messages, metadata, and settings of each chat model call."""

    def __init__(self) -> None:
        self.calls: list[list[BaseMessage]] = []
        self.metadata: list[dict[str, Any]] = []
        self.params: list[dict[str, Any]] = []

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        self.calls.extend(messages)
        self.metadata.append(kwargs.get("metadata") or {})
        self.params.append(kwargs.get("invocation_params") or {})


def fake_model(*replies: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(r) for r in replies]))


class FakeJudge:
    """Stands in for Jev: fixed answers, and a record of what it was asked.

    Questions not given an answer get 0.0, a clear "no".
    """

    def __init__(self, **answers: float) -> None:
        self.answers = {q: answers.get(q, 0.0) for q in QUESTIONS}
        self.asked: list[str] = []

    async def __call__(self, text: str) -> dict[str, float]:
        self.asked.append(text)
        return self.answers
