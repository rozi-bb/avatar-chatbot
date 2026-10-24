import pytest


@pytest.fixture(autouse=True)
def no_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Unit tests never call out, even when the shell has tracing turned on.
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
