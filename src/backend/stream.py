"""Turn the model's tokens into checked sentences Wayan can start speaking.

Each time a sentence ends, the whole reply so far goes through check_reply and
only the new part is sent. Because the stored reply is check_reply of the whole
text, what Wayan says adds up to exactly what the thread remembers
(docs/architecture.md §5).
"""

from __future__ import annotations

import re

from agent.reply import check_reply

SENTENCE_END = re.compile(r"[.!?…][\"'”’)]*\s")


class SentenceStream:
    """Collects tokens and hands back checked, not-yet-sent text."""

    def __init__(self) -> None:
        """Start with nothing received and nothing sent."""
        self.raw = ""
        self.sent = ""
        self.diverged = False

    def feed(self, token: str) -> list[str]:
        """Add a token; return new text to speak if a sentence just ended."""
        self.raw += token
        ends = [m.end() for m in SENTENCE_END.finditer(self.raw)]
        if not ends:
            return []
        return self._send(check_reply(self.raw[: ends[-1]]).text)

    def finish(self, final_text: str) -> list[str]:
        """Return whatever of the final, stored reply hasn't been sent yet."""
        return self._send(final_text)

    def _send(self, checked: str) -> list[str]:
        if self.diverged or not checked.startswith(self.sent):
            # The check changed earlier text (a late [help], say): what was
            # said can't be unsaid, so send nothing more.
            self.diverged = True
            return []
        new = checked[len(self.sent) :].strip()
        self.sent = checked
        return [new] if new else []
