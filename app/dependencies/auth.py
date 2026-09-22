import contextlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthenticatedError
from app.core.rbac import Role
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    subject: str
    role: Role | None = None


CredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


async def get_current_user(
    credentials: CredentialsDep = None,
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError()

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise UnauthenticatedError()

    raw_role = payload.get("role")
    role: Role | None = None

    if isinstance(raw_role, str):
        with contextlib.suppress(ValueError):
            role = Role(raw_role)

    return AuthenticatedUser(
        subject=subject,
        role=role,
    )


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]
