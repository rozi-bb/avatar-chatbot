# Roadmap — Wayan, the Little Host

The order of work, following the build canvas (*Vibe Code Chatbot Step by Step*). Product: [prd.md](prd.md) · Design: [architecture.md](architecture.md)

**Task size:** one task changes one file and takes under 15 minutes. Bigger means split it.
**Each AI session:** "Read docs/roadmap.md and do the next unchecked task."
**Each feature:** explain first → code → read the code yourself → test, and try it in `langgraph dev` → one commit. Evaluate it before starting the next feature.

Build steps 12 (login), 14 (plans; only its limits part is kept) and 15 (payment) are skipped, because this is a portfolio demo.

---

## Milestone 0 — Foundation (build steps 1–8)

- [x] Scaffold from `new-langgraph-project-python`; Python 3.13 with uv (step 1)
- [x] Git, `.gitignore`, `.env` and `.env.example`, first commit (step 2)
- [x] `AGENTS.md`, plus `CLAUDE.md` importing it (step 3)
- [x] `docs/prd.md`, with drafts of `knowledge/hotel.md` and `knowledge/bali-culture.md` (step 4)
- [x] `docs/architecture.md` (step 5)
- [x] `docs/roadmap.md` (step 6)
- [x] LangSmith tracing on (step 7)
- [x] Baseline graph: one `wayan` node with the persona prompt, unit tests, running in `langgraph dev` (checked through its API: three turns on one thread), with its traces in LangSmith (step 8)
- [x] Rozi chats with Wayan in Studio (Chrome) and reads a trace
- [x] Rozi reviews the docs and the hotel draft: name, story, facilities, culture notes (approved 2026-10-24)

## Milestone 1 — Memory (step 9.2)

- [x] Unit test: two turns on one thread with `InMemorySaver`; the second model call sees the first turn (plus: the next guest starts empty)
- [x] Try a multi-turn chat on one thread, and read its trace (through the dev server's API; Rozi tried Studio)
- [x] Add `session_id` and `channel` to the run metadata (`Context.channel`; on the model call)

## Milestone 2 — Reply contract (step 9.3, part 1)

- [x] `src/agent/reply.py`: `check_reply(text)` returns the cleaned text and `end_session`: tag whitelist, no markdown, JSON, emoji, or links, a 400-character cut at a sentence end
- [x] Unit tests for `check_reply`: tags, markdown, JSON, emoji, long text, `[bye]`, `[help]`
- [x] `end_session` in the state, and a `check_reply` node after `wayan`
- [x] Prompt: the `[bye]` rule
- [x] LangSmith dataset `wayan-format` and code evaluators for the format and `end_session` (step 17). 2026-10-24: both 100%. The first run exposed a JSON-wrapped reply the evaluator missed; both are fixed

## Milestone 3 — Knowledge and time (step 9.3, part 2)

- [x] Rozi approves `knowledge/*.md` (2026-10-24)
- [x] Read both files into the system prompt at startup, the fixed part first for caching (blockquote notes for editors left out)
- [x] `Context.now` and the current Bali time (Asia/Makassar) at the end of the system prompt (12- and 24-hour time)
- Seen without knowledge (2026-10-24), for the evals to catch: "the lobby always smells like fresh flowers", "I am a little wooden boy", "riding my bike"
- [x] Unit tests: the knowledge and the time appear in the prompt; a fixed `now` is used when given
- [x] LangSmith datasets `wayan-hotel-facts` (with "unknown" cases) and `wayan-culture`, with evaluators (step 17) 2026-10-24: all 100%, with an LLM judge for grounding. Fixed on the way: Wayan added details ("pancakes are famous", a wrong grandfather), denied things the facts don't mention (a gym), and misread 7 pm against "open until 8 pm" (fixed by low-effort thinking, see architecture.md §8)

## Milestone 4 — Guardrails and safety (step 9.4)

- [x] `screen_message` node: tidy and cut the text, keyword rules write `route` (`src/agent/screen.py`)
- [x] `fixed_reply` node, with all fixed lines (prd.md §11) in one module (`src/agent/lines.py`)
- [x] The `[help]` backstop in the prompt and in `check_reply`
- [x] English only: an Indonesian greeting got "Selamat pagi! Kabar baik, suksma…" (2026-10-24) Fixed in the prompt; checked by `wayan-injection`
- [x] Guardrail rules in the prompt (prd.md §10). The baseline asked a guest "What's your name?" on 2026-10-24; that must stop
- [x] Unit tests for routing: emergencies, requests for a person, and normal look-alikes ("can you help me find the spa?") (11 emergencies, 4 staff requests, 11 look-alikes)
- [x] LangSmith datasets `wayan-safety` and `wayan-injection` (step 17) 2026-10-24: all 100%. The model's [help] catches the emergencies the keyword rules miss ("collapsed", "won't wake up")

## Milestone 5 — Ending the conversation (step 9)

- [x] Prompt: when to add `[bye]`, and when not to ("thanks! and the pool?") (done in milestone 2)
- [x] LangSmith dataset `wayan-goodbye`: real goodbyes and look-alikes (step 17) 2026-10-24: 16 cases, both 100%. A later run ended a session for "I'm leaving Bali tomorrow. Any last fun fact?": the prompt now says a trip later isn't a goodbye, and code never ends a session when the guest's message asks something (the idle timer ends it instead). Three runs after that: 100%
- [ ] Human review: 10 conversations, scored for persona (prd.md §12). Transcripts ready for Rozi: `evals/review/persona-2026-10-24.md` (make new ones with `uv run python -m evals.review`)
- [x] Balinese words: at most one per reply and no repeats in a chat ("suksma" came up in almost every reply)

Human-in-the-loop (step 9.5) isn't needed in v1: every turn already ends by waiting for the guest.

## Milestone 6 — Backend (steps 10, 13, 18, 19)

- [x] FastAPI skeleton: health endpoint, settings from the environment (step 10) (`src/backend/app.py`, `settings.py`)
- [x] Speech-token endpoint, ported from the avatar's `server.py` (`speech.py`; the key never leaves the server)
- [x] `POST /sessions` (greeting stored in the thread) and `DELETE /sessions/{id}` (thread deleted)
- [x] `POST /sessions/{id}/messages`: checked sentence events, then `done` (step 13) (`stream.py`: the spoken sentences always add up to the stored reply). Live 2026-10-24: first sentence after 0.7–0.9 s
- [x] `POST /sessions/{id}/idle`: the 45 s and 60 s lines
- [x] Cut-ins: replace the last AI message with the part Wayan actually said (also when the guest cuts in before the reply arrived)
- [x] Limits: 20 turns, 300 characters, timeout → fixed lines (the limits part of step 14) (plus an optional daily budget, `DAILY_BUDGET_USD`, estimated in `budget.py`)
- [x] Business-flow tests (step 18) and security tests (step 19) (`tests/unit_tests/test_backend.py`: 12 flows, 8 security checks)

Step 11 (database) isn't planned: sessions live in memory and history lives in LangSmith. Revisit it if the daily spend cap must survive restarts.

## Milestone 7 — Kiosk page (step 16)

- [x] Copy the avatar page from `new_avatar_ai/web` into `web/`, served by the backend (the try-out panel became the kiosk panel; `speak(text)` now resolves when Wayan is done)
- [x] Start and Stop buttons, with the session calls
- [ ] Azure STT in continuous mode; cut-ins on recognized words. Built (phrase hints, echo filter, token refresh) and the cut-in path tested with typed words; still needs a try with a real microphone in Chrome, which the Browser pane blocks
- [x] A sentence queue for `speak()`; after a `[bye]` reply, end once Wayan finishes speaking
- [x] Idle timers: 45 s "still there?", 60 s goodbye (tried by calling the idle step directly, not by waiting)
- [x] Add the hotel's and Balinese words to `LOCAL_NAMES` (Taman, Gumitir, Swastiastu, suksma, …) (not yet heard by ear)
- [x] Measure the time from the guest's last word to Wayan's first sound 2026-10-24, typed in the test box (`?type=1`): median 1.94 s from sending the words to Wayan's first sound (1.11–2.52 s, 5 replies). Speech-to-text adds its end-of-speech wait on top

## Milestone 8 — Deploy and monitor (steps 20–26)

- [ ] VPS, domain, HTTPS, and separate production keys (steps 20–21)
- [ ] The daily spend cap and the providers' spending limits, before going public
- [ ] Monitoring: quality, cost per session against the budget, errors and uptime (steps 24–26)

Step 22 (database backups) isn't needed while there is no database.
