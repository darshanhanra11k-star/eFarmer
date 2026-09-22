from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.core.exceptions import UnauthenticatedError
from app.core.rbac import Role

_password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(
    subject: str,
    expires_minutes: int | None = None,
    role: Role | None = None,
) -> str:
    settings = get_settings()

    if expires_minutes is not None:
        if expires_minutes <= 0 or expires_minutes > 1440:
            raise ValueError("expires_minutes must be between 1 and 1440")
        minutes = expires_minutes
    else:
        minutes = settings.access_token_expire_minutes

    now = datetime.now(UTC)
    expire = now + timedelta(minutes=minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if role is not None:
        payload["role"] = role.value

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
        return dict(payload)
    except Exception:
        raise UnauthenticatedError() from None
