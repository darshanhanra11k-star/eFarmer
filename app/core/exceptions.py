from __future__ import annotations

from typing import Any, Final

DEFAULT_ERROR_CODE: Final[str] = "internal_error"
DEFAULT_ERROR_MESSAGE: Final[str] = "Something went wrong."
DEFAULT_ERROR_STATUS: Final[int] = 500


class AppError(Exception):
    __slots__ = ("code", "message", "status_code", "details")

    def __init__(
        self,
        *,
        code: str = DEFAULT_ERROR_CODE,
        message: str = DEFAULT_ERROR_MESSAGE,
        status_code: int = DEFAULT_ERROR_STATUS,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code: str = str(code)
        self.message: str = str(message)
        self.status_code: int = int(status_code)
        self.details: dict[str, Any] = dict(details) if details else {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
            "details": dict(self.details),
        }

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"code={self.code!r}, "
            f"status_code={self.status_code}, "
            f"message={self.message!r})"
        )

    def __str__(self) -> str:
        return self.message

    def __reduce__(self) -> tuple[Any, tuple[dict[str, Any]]]:
        return (
            _rebuild_app_error,
            (
                {
                    "code": self.code,
                    "message": self.message,
                    "status_code": self.status_code,
                    "details": dict(self.details),
                },
            ),
        )


def _rebuild_app_error(state: dict[str, Any]) -> AppError:
    return AppError(**state)


class NotFoundError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "The requested item was not found.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="not_found",
            message=message,
            status_code=404,
            details=details,
        )


class ConflictError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "This item needs review because the server has changed.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="conflict",
            message=message,
            status_code=409,
            details=details,
        )


class PermissionDeniedError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "You do not have permission to do this.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="permission_denied",
            message=message,
            status_code=403,
            details=details,
        )


class ValidationError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "Enter a valid value.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="validation_error",
            message=message,
            status_code=422,
            details=details,
        )


class UnauthenticatedError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "Please sign in again.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="unauthenticated",
            message=message,
            status_code=401,
            details=details,
        )


class IdempotencyConflictError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "This operation was already submitted.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="idempotency_conflict",
            message=message,
            status_code=409,
            details=details,
        )


class ServiceUnavailableError(AppError):
    __slots__ = ()

    def __init__(
        self,
        *,
        message: str = "The service is temporarily unavailable.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="service_unavailable",
            message=message,
            status_code=503,
            details=details,
        )
