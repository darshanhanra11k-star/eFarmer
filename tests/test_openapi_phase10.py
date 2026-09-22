from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


@pytest.fixture(autouse=True)
def _configure_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/farmer",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_openapi_schema_contains_phase10_endpoints() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"]
    assert "/api/v1/queues/{id}/join" in paths
    assert "/api/v1/queues/{id}" in paths
    assert "/api/v1/queues/{id}/call-next" in paths
    assert "/api/v1/tokens/{id}" in paths
    assert "/api/v1/tokens/{id}/process" in paths
    assert "/api/v1/tokens/{id}/complete" in paths
    assert "/api/v1/tokens/{id}/cancel" in paths

    join_post = paths["/api/v1/queues/{id}/join"]["post"]
    assert "201" in join_post["responses"]

    status_get = paths["/api/v1/queues/{id}"]["get"]
    assert "200" in status_get["responses"]

    call_next_post = paths["/api/v1/queues/{id}/call-next"]["post"]
    assert "200" in call_next_post["responses"]


def test_openapi_schemas_define_phase10_contracts() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    schemas = schema["components"]["schemas"]

    assert "TokenResponse" in schemas
    assert "QueueStatusResponse" in schemas

    token_props = schemas["TokenResponse"]["properties"]
    assert "token_number" in token_props
    assert "sequence_number" in token_props
    assert "status" in token_props
    assert "queue_id" in token_props
    assert "farmer_id" in token_props

    queue_status_props = schemas["QueueStatusResponse"]["properties"]
    assert "total_waiting" in queue_status_props
    assert "total_called" in queue_status_props
    assert "total_processing" in queue_status_props
    assert "total_completed" in queue_status_props
    assert "total_cancelled" in queue_status_props
