from collections.abc import Iterator

import pytest
from fastapi import APIRouter
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.exceptions import UnauthenticatedError
from app.core.security import create_access_token
from app.dependencies.auth import AuthenticatedUser, CurrentUserDep, get_current_user
from app.main import app

TEST_JWT_SECRET = "super_secret_test_key_that_is_at_least_32_characters_long"


@pytest.fixture(autouse=True)
def _configure_test_jwt(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/farmer"
    )
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_authorization_header_raises_unauthenticated() -> None:
    with pytest.raises(UnauthenticatedError):
        await get_current_user(None)


@pytest.mark.asyncio
async def test_scheme_is_not_bearer_raises_unauthenticated() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Basic",
        credentials="some_token",
    )
    with pytest.raises(UnauthenticatedError):
        await get_current_user(credentials)


@pytest.mark.asyncio
async def test_malformed_token_raises_unauthenticated() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.token",
    )
    with pytest.raises(UnauthenticatedError):
        await get_current_user(credentials)


@pytest.mark.asyncio
async def test_valid_token_returns_authenticated_user() -> None:
    token = create_access_token(subject="farmer_999")
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    user = await get_current_user(credentials)

    assert isinstance(user, AuthenticatedUser)
    assert user.subject == "farmer_999"


def test_test_route_with_current_user_returns_401_shape_on_failure() -> None:
    test_router = APIRouter()

    @test_router.get("/test-protected")
    def protected_route(_user: CurrentUserDep) -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(test_router)

    try:
        client = TestClient(app, raise_server_exceptions=False)

        # 1. Missing header
        res = client.get("/test-protected")
        assert res.status_code == 401
        body = res.json()
        assert body["code"] == "unauthenticated"
        assert body["message"] == "Please sign in again."
        assert body["status_code"] == 401
        assert body["details"] == {}

        # 2. Invalid token
        res_invalid = client.get(
            "/test-protected",
            headers={"Authorization": "Bearer not_a_valid_token"},
        )
        assert res_invalid.status_code == 401
        assert res_invalid.json()["code"] == "unauthenticated"

        # 3. Valid token
        token = create_access_token(subject="verified_user")
        res_valid = client.get(
            "/test-protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_valid.status_code == 200
        assert res_valid.json() == {"status": "ok"}
    finally:
        app.routes[:] = [
            r for r in app.routes if getattr(r, "path", None) != "/test-protected"
        ]
