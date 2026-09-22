from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.main import app


def test_ready_returns_200_when_db_is_available() -> None:
    async def override() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, AsyncMock(spec=AsyncSession))

    app.dependency_overrides[get_db_session] = override
    try:
        client = TestClient(app)
        response = client.get("/api/v1/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    finally:
        app.dependency_overrides.clear()


def test_ready_returns_503_when_db_is_unavailable() -> None:
    db_error_message = "could not connect to server: Connection refused"

    async def override() -> AsyncIterator[AsyncSession]:
        mock = AsyncMock(spec=AsyncSession)
        mock.execute.side_effect = RuntimeError(db_error_message)
        yield cast(AsyncSession, mock)

    app.dependency_overrides[get_db_session] = override
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["code"] == "service_unavailable"
        assert body["message"] == "The service is temporarily unavailable."
        assert body["status_code"] == 503
        assert body["details"] == {}

        response_text = response.text
        assert db_error_message not in response_text
        assert "postgresql" not in response_text.lower()
        assert "password" not in response_text.lower()
        assert "traceback" not in response_text.lower()
    finally:
        app.dependency_overrides.clear()
