from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import UnauthenticatedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

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


def test_hash_and_verify_password_happy_path() -> None:
    raw = "ValidPassword123!"
    hashed = hash_password(raw)

    assert verify_password(raw, hashed) is True


def test_verify_password_with_wrong_password_returns_false() -> None:
    hashed = hash_password("ValidPassword123!")

    assert verify_password("WrongPassword!", hashed) is False


def test_hash_is_not_equal_to_plaintext() -> None:
    raw = "ValidPassword123!"
    hashed = hash_password(raw)

    assert hashed != raw


def test_hash_changes_across_calls() -> None:
    raw = "ValidPassword123!"
    hash1 = hash_password(raw)
    hash2 = hash_password(raw)

    assert hash1 != hash2


def test_create_access_token_returns_str() -> None:
    token = create_access_token(subject="user_123")

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_returns_expected_claims() -> None:
    token = create_access_token(subject="farmer_456", expires_minutes=15)
    claims = decode_access_token(token)

    assert claims["sub"] == "farmer_456"
    assert "exp" in claims
    assert "iat" in claims


def test_decode_token_signed_with_different_secret_raises_unauthenticated() -> None:
    different_secret = "different_secret_key_at_least_32_chars_long_12345"
    now = datetime.now(UTC)
    payload = {
        "sub": "user_123",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    foreign_token = jwt.encode(payload, different_secret, algorithm="HS256")

    with pytest.raises(UnauthenticatedError):
        decode_access_token(foreign_token)


def test_decode_expired_token_raises_unauthenticated() -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": "user_123",
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
    }
    expired_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(UnauthenticatedError):
        decode_access_token(expired_token)


def test_decode_malformed_token_raises_unauthenticated() -> None:
    with pytest.raises(UnauthenticatedError):
        decode_access_token("not.a.valid.jwt.token")


def test_decode_token_with_algorithm_none_raises_unauthenticated() -> None:
    now = datetime.now(UTC)
    payload = {
        "sub": "user_123",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    none_token = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(UnauthenticatedError):
        decode_access_token(none_token)


def test_create_access_token_with_invalid_expires_minutes_raises_value_error() -> None:
    with pytest.raises(ValueError):
        create_access_token(subject="user_123", expires_minutes=0)

    with pytest.raises(ValueError):
        create_access_token(subject="user_123", expires_minutes=-5)

    with pytest.raises(ValueError):
        create_access_token(subject="user_123", expires_minutes=1441)
