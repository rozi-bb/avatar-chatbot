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
- [ ] Rozi chats with Wayan in Studio (Chrome) and reads a trace
- [ ] Rozi reviews the docs and the hotel draft: name, story, facilities, culture notes

## Milestone 1 — Memory (step 9.2)

- [x] Unit test: two turns on one thread with `InMemorySaver`; the second model call sees the first turn (plus: the next guest starts empty)
- [x] Try a multi-turn chat on one thread, and read its trace (through the dev server's API; Rozi tried Studio)
- [x] Add `session_id` and `channel` to the run metadata (`Context.channel`; on the model call)

## Milestone 2 — Reply contract (step 9.3, part 1)

- [ ] `src/agent/reply.py`: `check_reply(text)` returns the cleaned text and `end_session`: tag whitelist, no markdown, emoji, or links, a 400-character cut at a sentence end
- [ ] Unit tests for `check_reply`: tags, markdown, emoji, long text, `[bye]`, `[help]`
- [ ] `end_session` in the state, and a `check_reply` node after `wayan`
- [ ] Prompt: the `[bye]` rule
- [ ] LangSmith dataset `wayan-format` and a code evaluator for the format (step 17)

## Milestone 3 — Knowledge and time (step 9.3, part 2)

- [ ] Rozi approves `knowledge/*.md`
- [ ] Read both files into the system prompt at startup, the fixed part first for caching
- [ ] `Context.now` and the current Bali time (Asia/Makassar) at the end of the system prompt
- [ ] Unit tests: the knowledge and the time appear in the prompt; a fixed `now` is used when given
- [ ] LangSmith datasets `wayan-hotel-facts` (with "unknown" cases) and `wayan-culture`, with evaluators (step 17)

## Milestone 4 — Guardrails and safety (step 9.4)

- [ ] `screen_message` node: tidy and cut the text, keyword rules write `route`
- [ ] `fixed_reply` node, with all fixed lines (prd.md §11) in one module
- [ ] The `[help]` backstop in the prompt and in `check_reply`
- [ ] Guardrail rules in the prompt (prd.md §10). The baseline asked a guest "What's your name?" on 2026-10-24; that must stop
- [ ] Unit tests for routing: emergencies, requests for a person, and normal look-alikes ("can you help me find the spa?")
- [ ] LangSmith datasets `wayan-safety` and `wayan-injection` (step 17)

## Milestone 5 — Ending the conversation (step 9)

- [ ] Prompt: when to add `[bye]`, and when not to ("thanks! and the pool?")
- [ ] LangSmith dataset `wayan-goodbye`: real goodbyes and look-alikes (step 17)
- [ ] Human review: 10 conversations, scored for persona (prd.md §12)

Human-in-the-loop (step 9.5) isn't needed in v1: every turn already ends by waiting for the guest.

## Milestone 6 — Backend (steps 10, 13, 18, 19)

- [ ] FastAPI skeleton: health endpoint, settings from the environment (step 10)
- [ ] Speech-token endpoint, ported from the avatar's `server.py`
- [ ] `POST /sessions` (greeting stored in the thread) and `DELETE /sessions/{id}` (thread deleted)
- [ ] `POST /sessions/{id}/messages`: checked sentence events, then `done` (step 13)
- [ ] `POST /sessions/{id}/idle`: the 45 s and 60 s lines
- [ ] Cut-ins: replace the last AI message with the part Wayan actually said
- [ ] Limits: 20 turns, 300 characters, timeout → fixed lines (the limits part of step 14)
- [ ] Business-flow tests (step 18) and security tests (step 19)

Step 11 (database) isn't planned: sessions live in memory and history lives in LangSmith. Revisit it if the daily spend cap must survive restarts.

## Milestone 7 — Kiosk page (step 16)

- [ ] Copy the avatar page from `new_avatar_ai/web` into `web/`, served by the backend
- [ ] Start and Stop buttons, with the session calls
- [ ] Azure STT in continuous mode; cut-ins on recognized words
- [ ] A sentence queue for `speak()`; after a `[bye]` reply, end once Wayan finishes speaking
- [ ] Idle timers: 45 s "still there?", 60 s goodbye
- [ ] Add the hotel's and Balinese words to `LOCAL_NAMES` (Taman, Gumitir, Swastiastu, suksma, …)
- [ ] Measure the time from the guest's last word to Wayan's first sound

## Milestone 8 — Deploy and monitor (steps 20–26)

- [ ] VPS, domain, HTTPS, and separate production keys (steps 20–21)
- [ ] The daily spend cap and the providers' spending limits, before going public
- [ ] Monitoring: quality, cost per session against the budget, errors and uptime (steps 24–26)

Step 22 (database backups) isn't needed while there is no database.
