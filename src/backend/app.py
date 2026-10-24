"""The kiosk's backend (docs/architecture.md §3): one FastAPI server.

It serves the kiosk page, hands out Azure speech tokens, keeps each guest's
session, and streams Wayan's replies as checked sentences. Run it with:

    uv run uvicorn backend.app:build_app --factory --port 8000
"""

from __future__ import annotations

import json
import logging
import random
import re
from collections.abc import AsyncIterator
from typing import Any, Literal, cast

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

from agent import lines
from agent.graph import Context, build_graph
from agent.reply import check_reply
from agent.screen import MAX_GUEST_CHARS
from backend.budget import DailyBudget, reply_cost
from backend.sessions import Session, SessionStore
from backend.settings import ROOT, Settings
from backend.speech import SpeechTokenError, SpeechTokens
from backend.stream import SentenceStream

log = logging.getLogger(__name__)

MAX_TEXT_CHARS = 2000
"""Longest request text accepted at all; the screen then cuts it to 300."""


class Interrupted(BaseModel):
    """What Wayan had said when the guest cut in.

    Attributes:
        message_id: The reply that was cut, from its `done` event. None if the
            guest cut in before the reply finished arriving.
        spoken_text: The part the guest actually heard, tags allowed.
    """

    message_id: str | None = None
    spoken_text: str = Field(default="", max_length=MAX_TEXT_CHARS)


class GuestMessage(BaseModel):
    """A guest's words, as recognized by speech-to-text."""

    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    interrupted: Interrupted | None = None


class Idle(BaseModel):
    """Which idle moment the kiosk reached: 45 s ("check") or 60 s ("end")."""

    stage: Literal["check", "end"]


def sse(event: str, data: dict[str, Any]) -> str:
    """Format one server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def thread(session_id: str) -> RunnableConfig:
    """Return the run config for a session's thread."""
    return {"configurable": {"thread_id": session_id}}


def create_app(
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    speech_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the backend.

    Args:
        model: Chat model for Wayan. Defaults to DeepSeek; tests pass a fake.
        settings: Defaults to the environment.
        speech_transport: Lets tests fake Azure's token service.
    """
    settings = settings or Settings.from_env()
    checkpointer = InMemorySaver()
    graph = build_graph(model, checkpointer=checkpointer)
    sessions = SessionStore(settings.idle_session_minutes)
    budget = DailyBudget(settings.daily_budget_usd)
    tokens = SpeechTokens(
        settings.azure_speech_key, settings.azure_speech_region, speech_transport
    )

    app = FastAPI(title="Wayan kiosk backend")
    app.state.graph = graph
    app.state.sessions = sessions
    app.state.budget = budget

    async def remember(session_id: str, said: list[BaseMessage]) -> None:
        """Write messages into the thread as if Wayan's turn had just ended."""
        await graph.aupdate_state(
            thread(session_id), {"messages": said}, as_node="check_reply"
        )

    async def end(session_id: str) -> None:
        sessions.end(session_id)
        await checkpointer.adelete_thread(session_id)

    async def clear_abandoned() -> None:
        for session_id in sessions.abandoned():
            await checkpointer.adelete_thread(session_id)

    def live(session_id: str) -> Session:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="No such session")
        return session

    async def keep_spoken_part(session_id: str, cut: Interrupted) -> None:
        """Make the thread remember only what the guest heard before cutting in."""
        words = re.sub(r"\[[^\]]*\]", "", cut.spoken_text)
        heard = None
        if re.search(r"[A-Za-z0-9]", words):
            heard = check_reply(cut.spoken_text.strip().rstrip(".!?… ") + "…").text
        said: list[BaseMessage]
        if cut.message_id:
            # Same ID: add_messages replaces the reply, or removes it if nothing was heard.
            said = [
                AIMessage(heard, id=cut.message_id)
                if heard
                else RemoveMessage(id=cut.message_id)
            ]
        elif heard:
            said = [AIMessage(heard)]
        else:
            return
        await remember(session_id, said)

    async def last_words(session: Session, line: str) -> AsyncIterator[str]:
        """Say a fixed goodbye line and end the session."""
        yield sse("sentence", {"index": 0, "text": line})
        yield sse("done", {"message_id": None, "end_session": True})
        await end(session.id)

    async def reply_stream(session: Session, text: str) -> AsyncIterator[str]:
        """Run Wayan on the guest's words and stream his checked sentences."""
        if session.turns >= settings.max_turns:
            async for event in last_words(session, lines.TURN_LIMIT):
                yield event
            return
        if budget.used_up():
            async for event in last_words(session, lines.RESTING):
                yield event
            return
        session.turns += 1

        stream = SentenceStream()
        index = 0
        final: AnyMessage | None = None
        end_session = False
        guest: list[AnyMessage] = [HumanMessage(text[:MAX_GUEST_CHARS])]
        try:
            async for item in graph.astream(
                {"messages": guest},
                thread(session.id),
                context=Context(channel="kiosk"),
                stream_mode=["messages", "updates"],
            ):
                mode, data = cast("tuple[str, Any]", item)
                if mode == "messages":
                    chunk, meta = data
                    if meta.get("langgraph_node") == "wayan" and chunk.text:
                        for piece in stream.feed(chunk.text):
                            yield sse("sentence", {"index": index, "text": piece})
                            index += 1
                    continue
                for node in ("check_reply", "fixed_reply"):
                    if node in data:
                        final = data[node]["messages"][-1]
                        end_session = bool(data[node].get("end_session"))
        except Exception:
            log.exception("Wayan's reply failed in session %s", session.id)
            yield sse("error", {"text": lines.ERROR})
            return
        if final is None:
            yield sse("error", {"text": lines.ERROR})
            return

        for piece in stream.finish(final.text):
            yield sse("sentence", {"index": index, "text": piece})
            index += 1
        budget.add(reply_cost(getattr(final, "usage_metadata", None), final.text))
        yield sse("done", {"message_id": final.id, "end_session": end_session})
        if end_session:
            await end(session.id)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Say the server is up, and how many sessions are live."""
        return {"ok": True, "sessions": len(sessions.sessions)}

    @app.get("/api/speech-token")
    async def speech_token() -> JSONResponse:
        """Return a short-lived Azure Speech token; the key stays here."""
        try:
            token, region = await tokens.get()
        except SpeechTokenError as err:
            return JSONResponse({"error": str(err)}, status_code=503)
        except httpx.HTTPError:
            return JSONResponse(
                {"error": "Azure could not be reached"}, status_code=503
            )
        return JSONResponse(
            {"token": token, "region": region}, headers={"Cache-Control": "no-store"}
        )

    @app.post("/sessions")
    async def start_session() -> dict[str, str]:
        """Start a session when the guest presses Start; Wayan greets first."""
        await clear_abandoned()
        session = sessions.start()
        greeting = random.choice(lines.GREETINGS)
        await remember(session.id, [AIMessage(greeting)])
        return {"session_id": session.id, "greeting": greeting}

    @app.post("/sessions/{session_id}/messages")
    async def guest_message(session_id: str, body: GuestMessage) -> StreamingResponse:
        """Stream Wayan's reply to what the guest said."""
        session = live(session_id)
        if body.interrupted:
            await keep_spoken_part(session_id, body.interrupted)
        return StreamingResponse(
            reply_stream(session, body.text),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/sessions/{session_id}/idle")
    async def idle(session_id: str, body: Idle) -> dict[str, Any]:
        """Return the 45 s "still there?" line, or the 60 s goodbye that ends the session."""
        live(session_id)
        if body.stage == "end":
            await end(session_id)
            return {"text": lines.IDLE_GOODBYE, "end_session": True}
        await remember(session_id, [AIMessage(lines.STILL_THERE)])
        return {"text": lines.STILL_THERE, "end_session": False}

    @app.delete("/sessions/{session_id}", status_code=204)
    async def stop(session_id: str) -> Response:
        """End a session when the guest presses Stop."""
        live(session_id)
        await end(session_id)
        return Response(status_code=204)

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="kiosk")
    return app


def build_app() -> FastAPI:
    """Create the app with settings and keys from .env (the uvicorn factory)."""
    load_dotenv(ROOT / ".env")
    logging.basicConfig(level=logging.INFO)
    return create_app()
