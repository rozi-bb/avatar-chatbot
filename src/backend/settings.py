"""Backend settings, read from the environment (.env in development)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """What the backend needs to know; the defaults come from docs/prd.md §13.

    Attributes:
        azure_speech_key: Azure Speech key; stays on the server.
        azure_speech_region: Azure region of that key.
        max_turns: Guest turns per session before Wayan says goodbye.
        idle_session_minutes: A session left alone this long is cleared.
        daily_budget_usd: Estimated spend per Bali day; None means no cap.
        web_dir: The kiosk page served at "/", if the folder exists.
    """

    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    max_turns: int = 20
    idle_session_minutes: int = 15
    daily_budget_usd: float | None = None
    web_dir: Path = field(default=ROOT / "web")

    @classmethod
    def from_env(cls) -> Settings:
        """Read the settings from environment variables."""
        budget = os.environ.get("DAILY_BUDGET_USD")
        return cls(
            azure_speech_key=os.environ.get("AZURE_SPEECH_KEY") or None,
            azure_speech_region=os.environ.get("AZURE_SPEECH_REGION") or None,
            max_turns=int(os.environ.get("MAX_TURNS", "20")),
            daily_budget_usd=float(budget) if budget else None,
        )
