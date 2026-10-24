# Wayan, the Little Host

A voice chatbot for the lobby kiosk of Taman Gumitir, a fictional heritage hotel in Bali. Wayan, an animated Balinese boy, answers guests in short, cheerful, spoken English. A portfolio demo.

This repo is Wayan's brain: a [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) agent on DeepSeek, traced in LangSmith. The avatar itself (Rive rig, Azure TTS, lip sync, subtitles) lives in `rozi-bb/wayan-avatar`.

| Document | What it covers |
|---|---|
| [docs/prd.md](docs/prd.md) | What we build and why |
| [docs/architecture.md](docs/architecture.md) | How it is built |
| [docs/roadmap.md](docs/roadmap.md) | Order of work and progress |
| [knowledge/](knowledge/) | What Wayan knows: the hotel and Balinese culture |

## Setup

You need [uv](https://docs.astral.sh/uv/), a DeepSeek API key, and a LangSmith API key.

```bash
uv sync
cp .env.example .env    # then fill in the two keys
```

## Run

The kiosk (backend and page): open http://127.0.0.1:8000 in Chrome, press Start, and talk.

```bash
uv run uvicorn backend.app:build_app --factory --port 8000
```

It needs a microphone; for testing without one, open http://127.0.0.1:8000/?type=1 and type what a guest would say. The backend needs the Azure Speech key too (see `.env.example`).

For developing the agent alone:

```bash
uv run langgraph dev
```

This starts the local API at http://127.0.0.1:2024. Open Studio at https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024 to chat with Wayan and watch the graph. Use Chrome: Safari blocks Studio from reaching localhost (`uv run langgraph dev --tunnel` works around that).

Every run is traced to the LangSmith project `avatar-chatbot`.

## Test

```bash
uv run pytest -q                    # unit tests, no API calls
uv run pytest -q -m integration     # integration tests: real DeepSeek calls
uv run ruff check .                 # lint
uv run mypy --strict src evals      # type check
uv run python -m evals.run          # LangSmith evaluations: real DeepSeek calls
```
