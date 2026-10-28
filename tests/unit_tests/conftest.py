import sys

import pytest

import agent.graph  # noqa: F401  (loads the module patched below)
from unit_tests.fakes import FakeJudge


@pytest.fixture(autouse=True)
def no_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Unit tests never call out, even when the shell has tracing turned on.
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


@pytest.fixture(autouse=True)
def quiet_jev(monkeypatch: pytest.MonkeyPatch) -> None:
    # Nor do they ask Jev: the screen's second look says "no" to everything.
    # `agent.graph` names the compiled graph, so patch the module itself.
    monkeypatch.setattr(sys.modules["agent.graph"], "default_judge", FakeJudge)
