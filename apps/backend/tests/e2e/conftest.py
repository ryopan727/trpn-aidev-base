import httpx
import pytest


@pytest.fixture
def http_api(db_pool):
    # Compose starts api-test separately; no app instance or ASGI transport here.
    # A fixed internal service name prevents falling back to the development API.
    with httpx.Client(
        base_url="http://api-test:8000", timeout=10, trust_env=False
    ) as client:
        yield client
