import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import AppError


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    async def app_error() -> None:
        raise AppError(
            code="TEST_ERROR",
            message="Test error.",
            status_code=409,
            details={"field": "value"},
        )

    @app.get("/unexpected-error")
    async def unexpected_error() -> None:
        raise RuntimeError("Unexpected failure.")

    @app.post("/validation-error")
    async def validation_error(payload: dict[str, int]) -> dict[str, int]:
        return payload

    return app


def test_app_error_handler(app: FastAPI) -> None:
    client = TestClient(app)

    response = client.get("/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "TEST_ERROR",
        "message": "Test error.",
        "status_code": 409,
        "details": {"field": "value"},
    }


def test_unexpected_error_handler(app: FastAPI) -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Something went wrong.",
        "status_code": 500,
        "details": {},
    }


def test_request_validation_error_handler(app: FastAPI) -> None:
    client = TestClient(app)

    response = client.post("/validation-error", json={"key": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "Enter a valid value."
    assert body["status_code"] == 422
    assert "errors" in body["details"]
    assert isinstance(body["details"]["errors"], list)
    assert len(body["details"]["errors"]) > 0
