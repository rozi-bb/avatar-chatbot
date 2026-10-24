"""The kiosk's business flows (build step 18) and security checks (step 19)."""

import json
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from agent import lines
from agent.reply import check_reply
from backend.app import create_app
from backend.settings import Settings
from unit_tests.fakes import fake_model

pytestmark = pytest.mark.anyio

FAKE_KEY = "fake-azure-key-for-tests"


def azure(status: int = 200, token: str = "token-123") -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.headers["Ocp-Apim-Subscription-Key"] == FAKE_KEY
        return httpx.Response(status, text=token if status == 200 else "bad key")

    return httpx.MockTransport(handle)


def kiosk(
    *replies: str, model: GenericFakeChatModel | None = None, **settings: Any
) -> AsyncClient:
    config = Settings(
        azure_speech_key=FAKE_KEY,
        azure_speech_region="southeastasia",
        web_dir=Path("/no/kiosk/page"),
        **settings,
    )
    app = create_app(model or fake_model(*replies), config, speech_transport=azure())
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://kiosk")


def events(body: str) -> list[tuple[str, dict[str, Any]]]:
    found = []
    for block in body.strip().split("\n\n"):
        event = re.search(r"^event: (.+)$", block, re.M)
        data = re.search(r"^data: (.+)$", block, re.M)
        assert event and data
        found.append((event.group(1), json.loads(data.group(1))))
    return found


async def start(client: AsyncClient) -> str:
    response = await client.post("/sessions")
    assert response.status_code == 200
    return str(response.json()["session_id"])


async def say(
    client: AsyncClient, session_id: str, text: str, **extra: Any
) -> list[tuple[str, dict[str, Any]]]:
    response = await client.post(
        f"/sessions/{session_id}/messages", json={"text": text, **extra}
    )
    assert response.status_code == 200
    return events(response.text)


def spoken(found: list[tuple[str, dict[str, Any]]]) -> str:
    return " ".join(data["text"] for event, data in found if event == "sentence")


async def thread_messages(client: AsyncClient, session_id: str) -> list[Any]:
    app = client._transport.app  # type: ignore[attr-defined]
    state = await app.state.graph.aget_state(
        {"configurable": {"thread_id": session_id}}
    )
    return list(state.values.get("messages", []))


# Business flows


async def test_start_greets_first_and_remembers_the_greeting() -> None:
    async with kiosk() as client:
        response = await client.post("/sessions")
        body = response.json()

        assert body["greeting"] in lines.GREETINGS
        assert uuid.UUID(body["session_id"]).version == 4
        [greeting] = await thread_messages(client, body["session_id"])
        assert greeting.text == body["greeting"]


async def test_a_reply_streams_as_checked_sentences() -> None:
    async with kiosk("Hi **friend**! I'm Wayan. Want a fun fact? 😀") as client:
        session_id = await start(client)

        found = await say(client, session_id, "Hi!")

        stored = (await thread_messages(client, session_id))[-1]
        assert [e for e, _ in found] == ["sentence", "sentence", "sentence", "done"]
        assert (
            spoken(found)
            == stored.text
            == check_reply("Hi friend! I'm Wayan. Want a fun fact?").text
        )
        assert found[-1][1] == {"message_id": stored.id, "end_session": False}


async def test_a_goodbye_ends_the_session() -> None:
    async with kiosk("[smile] Bye bye! [bye]") as client:
        session_id = await start(client)

        found = await say(client, session_id, "Bye Wayan!")

        assert found[-1][1]["end_session"] is True
        assert (
            await client.post(f"/sessions/{session_id}/messages", json={"text": "Hi"})
        ).status_code == 404


async def test_an_emergency_gets_the_fixed_line() -> None:
    async with kiosk() as client:
        session_id = await start(client)

        found = await say(client, session_id, "Help! My daughter is lost!")

        assert spoken(found) == lines.EMERGENCY


async def test_the_turn_limit_says_goodbye_and_ends() -> None:
    async with kiosk("[smile] Hi!", max_turns=1) as client:
        session_id = await start(client)
        await say(client, session_id, "Hi!")

        found = await say(client, session_id, "Tell me more!")

        assert spoken(found) == lines.TURN_LIMIT
        assert found[-1][1]["end_session"] is True
        assert (await client.delete(f"/sessions/{session_id}")).status_code == 404


async def test_a_used_up_budget_makes_wayan_rest() -> None:
    async with kiosk("[smile] Hi!", daily_budget_usd=0.0) as client:
        session_id = await start(client)

        found = await say(client, session_id, "Hi!")

        assert spoken(found) == lines.RESTING


async def test_silence_first_checks_then_says_goodbye() -> None:
    async with kiosk() as client:
        session_id = await start(client)

        check = await client.post(
            f"/sessions/{session_id}/idle", json={"stage": "check"}
        )
        assert check.json() == {"text": lines.STILL_THERE, "end_session": False}
        assert (await thread_messages(client, session_id))[-1].text == lines.STILL_THERE

        end = await client.post(f"/sessions/{session_id}/idle", json={"stage": "end"})
        assert end.json() == {"text": lines.IDLE_GOODBYE, "end_session": True}
        assert (await client.delete(f"/sessions/{session_id}")).status_code == 404


async def test_a_cut_in_keeps_only_what_was_heard() -> None:
    story = "[smile] Once upon a time there was a duck. He marched every day. The end!"
    async with kiosk(story, "[smile] Okay!") as client:
        session_id = await start(client)
        first = await say(client, session_id, "Tell me a story")
        message_id = first[-1][1]["message_id"]

        cut = {
            "message_id": message_id,
            "spoken_text": "[smile] Once upon a time there was a duck. He marched",
        }
        await say(client, session_id, "Wait, stop!", interrupted=cut)

        messages = await thread_messages(client, session_id)
        assert [m.type for m in messages] == ["ai", "human", "ai", "human", "ai"]
        assert messages[2].id == message_id
        assert (
            messages[2].text == "[smile] Once upon a time there was a duck. He marched…"
        )


async def test_a_cut_in_before_the_reply_arrived_is_still_remembered() -> None:
    async with kiosk("[smile] Okay!") as client:
        session_id = await start(client)

        await say(
            client,
            session_id,
            "Stop!",
            interrupted={"spoken_text": "[smile] Hello there"},
        )

        messages = await thread_messages(client, session_id)
        assert [m.text for m in messages[1:3]] == ["[smile] Hello there…", "Stop!"]


async def test_stop_ends_the_session() -> None:
    async with kiosk() as client:
        session_id = await start(client)

        assert (await client.delete(f"/sessions/{session_id}")).status_code == 204
        assert await thread_messages(client, session_id) == []


async def test_a_model_failure_sends_the_error_line() -> None:
    async with kiosk() as client:  # the fake model has no replies, so it fails
        session_id = await start(client)

        found = await say(client, session_id, "Hi!")

        assert found == [("error", {"text": lines.ERROR})]


async def test_speech_token_comes_from_azure() -> None:
    async with kiosk() as client:
        response = await client.get("/api/speech-token")

        assert response.json() == {"token": "token-123", "region": "southeastasia"}
        assert response.headers["cache-control"] == "no-store"


# Security


async def test_the_azure_key_never_leaves_the_server() -> None:
    config = Settings(
        azure_speech_key=FAKE_KEY,
        azure_speech_region="southeastasia",
        web_dir=Path("/x"),
    )
    for transport in (azure(), azure(status=401)):
        app = create_app(fake_model(), config, speech_transport=transport)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://kiosk"
        ) as client:
            response = await client.get("/api/speech-token")
            assert FAKE_KEY not in response.text


async def test_a_bad_azure_key_is_a_clean_error() -> None:
    config = Settings(
        azure_speech_key=FAKE_KEY,
        azure_speech_region="southeastasia",
        web_dir=Path("/x"),
    )
    app = create_app(fake_model(), config, speech_transport=azure(status=401))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://kiosk"
    ) as client:
        response = await client.get("/api/speech-token")

        assert response.status_code == 503
        assert "401" in response.json()["error"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/messages", {"text": "Hi"}),
        ("post", "/idle", {"stage": "check"}),
        ("delete", "", None),
    ],
)
async def test_unknown_sessions_are_refused(
    method: str, path: str, body: dict[str, Any] | None
) -> None:
    async with kiosk() as client:
        url = f"/sessions/{uuid.uuid4()}{path}"
        response = await (
            client.post(url, json=body) if method == "post" else client.delete(url)
        )

        assert response.status_code == 404


@pytest.mark.parametrize("text", ["", "x" * 2001])
async def test_empty_or_huge_messages_are_refused(text: str) -> None:
    async with kiosk() as client:
        session_id = await start(client)

        response = await client.post(
            f"/sessions/{session_id}/messages", json={"text": text}
        )

        assert response.status_code == 422


async def test_sessions_never_see_each_other() -> None:
    async with kiosk("[smile] Hi Ana!", "[smile] Hi Ben!") as client:
        ana, ben = await start(client), await start(client)

        await say(client, ana, "I'm Ana")
        await say(client, ben, "I'm Ben")

        assert ana != ben
        assert "Ana" not in " ".join(m.text for m in await thread_messages(client, ben))


async def test_other_websites_cannot_call_the_backend() -> None:
    async with kiosk() as client:
        response = await client.post(
            "/sessions", headers={"Origin": "https://evil.example"}
        )

        assert "access-control-allow-origin" not in response.headers
