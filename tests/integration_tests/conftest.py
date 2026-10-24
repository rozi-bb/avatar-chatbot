import pytest
from dotenv import load_dotenv


@pytest.fixture(autouse=True, scope="session")
def env_keys() -> None:
    # Loaded here, not at import, so collecting unit tests never picks up the
    # keys or turns tracing on.
    load_dotenv()
