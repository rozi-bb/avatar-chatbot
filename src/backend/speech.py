"""Short-lived Azure Speech tokens, so the key never reaches the kiosk page.

Ported from the avatar's server.py: the page asks for a token, the server
trades its key for a 10-minute token and reuses it for 8 minutes.
"""

from __future__ import annotations

import time

import httpx

TOKEN_TTL_SECONDS = 8 * 60


class SpeechTokenError(RuntimeError):
    """Azure didn't give a token; the message is safe to show (no key in it)."""


class SpeechTokens:
    """Hands out cached Azure Speech tokens for one key and region."""

    def __init__(
        self,
        key: str | None,
        region: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Keep the key and region; `transport` lets tests fake Azure."""
        self.key = key
        self.region = region
        self.transport = transport
        self.token: str | None = None
        self.expires = 0.0

    async def get(self) -> tuple[str, str]:
        """Return a valid (token, region), asking Azure only when the cached one is old."""
        if not self.key or not self.region:
            raise SpeechTokenError(
                "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are not set"
            )
        if self.token and time.monotonic() < self.expires:
            return self.token, self.region
        url = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        async with httpx.AsyncClient(transport=self.transport, timeout=10) as client:
            response = await client.post(
                url, headers={"Ocp-Apim-Subscription-Key": self.key}
            )
        if response.status_code != 200:
            raise SpeechTokenError(
                f"Azure refused the key (HTTP {response.status_code})"
            )
        self.token = response.text
        self.expires = time.monotonic() + TOKEN_TTL_SECONDS
        return self.token, self.region
