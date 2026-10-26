"""Kiosk sessions: one guest's conversation, from Start until it ends.

A session is a LangGraph thread plus a little bookkeeping. Sessions live in
memory: they last minutes and nothing should outlive them (docs/prd.md §8).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from agent.lines import Language


@dataclass
class Session:
    """One guest's conversation.

    Attributes:
        id: Random and unguessable; also the LangGraph thread_id.
        turns: Guest messages answered so far.
        last_seen: When the kiosk last used this session (monotonic seconds).
        language: What Wayan speaks in this session, picked before Start.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turns: int = 0
    last_seen: float = field(default_factory=time.monotonic)
    language: Language = "en"


class SessionStore:
    """The live sessions, by ID."""

    def __init__(self, idle_minutes: int) -> None:
        """Clear sessions left alone for `idle_minutes` (a kiosk that crashed)."""
        self.idle_seconds = idle_minutes * 60
        self.sessions: dict[str, Session] = {}

    def start(self, language: Language = "en") -> Session:
        """Open a new session in the guest's language."""
        session = Session(language=language)
        self.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Return a live session and mark it as used, or None."""
        session = self.sessions.get(session_id)
        if session:
            session.last_seen = time.monotonic()
        return session

    def end(self, session_id: str) -> bool:
        """Close a session; return False if there was none."""
        return self.sessions.pop(session_id, None) is not None

    def abandoned(self) -> list[str]:
        """Remove and return the sessions nobody has used for too long."""
        cutoff = time.monotonic() - self.idle_seconds
        old = [s.id for s in self.sessions.values() if s.last_seen < cutoff]
        for session_id in old:
            del self.sessions[session_id]
        return old
