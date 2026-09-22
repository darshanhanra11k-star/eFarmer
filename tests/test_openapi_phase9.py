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


def test_openapi_schema_contains_phase9_endpoints() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    paths = schema["paths"]
    assert "/api/v1/farmers" in paths
    assert "/api/v1/farmers/{id}" in paths
    assert "/api/v1/centres" in paths
    assert "/api/v1/centres/{id}" in paths

    farmers_post = paths["/api/v1/farmers"]["post"]
    assert "201" in farmers_post["responses"]
    assert "requestBody" in farmers_post

    farmer_get = paths["/api/v1/farmers/{id}"]["get"]
    assert "200" in farmer_get["responses"]

    centres_get = paths["/api/v1/centres"]["get"]
    assert "200" in centres_get["responses"]

    centre_get = paths["/api/v1/centres/{id}"]["get"]
    assert "200" in centre_get["responses"]


def test_openapi_schemas_define_contracts() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    schemas = schema["components"]["schemas"]

    assert "FarmerCreate" in schemas
    assert "FarmerResponse" in schemas
    assert "CentreResponse" in schemas

    farmer_create_props = schemas["FarmerCreate"]["properties"]
    assert "farmer_id" in farmer_create_props
    assert "name" in farmer_create_props
    assert "phone" in farmer_create_props
    assert "mobile" not in farmer_create_props
    assert "password_hash" not in farmer_create_props

    farmer_response_props = schemas["FarmerResponse"]["properties"]
    assert "farmer_id" in farmer_response_props
    assert "name" in farmer_response_props
    assert "phone" in farmer_response_props
    assert "mobile" not in farmer_response_props
    assert "password_hash" not in farmer_response_props
