import pickle

import pytest

from app.core.exceptions import (
    DEFAULT_ERROR_CODE,
    DEFAULT_ERROR_MESSAGE,
    DEFAULT_ERROR_STATUS,
    AppError,
    ConflictError,
    IdempotencyConflictError,
    NotFoundError,
    PermissionDeniedError,
    ServiceUnavailableError,
    UnauthenticatedError,
    ValidationError,
)


def test_app_error_stores_data() -> None:
    error = AppError(
        code="TEST_ERROR",
        message="Test message.",
        details={"field": "value"},
    )

    assert error.code == "TEST_ERROR"
    assert error.message == "Test message."
    assert error.details == {"field": "value"}
    assert str(error) == "Test message."


def test_app_error_details_are_copied() -> None:
    details = {"field": "value"}

    error = AppError(
        code="TEST_ERROR",
        message="Test message.",
        details=details,
    )

    details["field"] = "changed"

    assert error.details == {"field": "value"}


def test_app_error_can_be_raised() -> None:
    with pytest.raises(AppError) as exc_info:
        raise AppError(
            code="TEST_ERROR",
            message="Test message.",
        )

    assert exc_info.value.code == "TEST_ERROR"


def test_app_error_defaults() -> None:
    error = AppError()

    assert error.code == DEFAULT_ERROR_CODE
    assert error.message == DEFAULT_ERROR_MESSAGE
    assert error.status_code == DEFAULT_ERROR_STATUS
    assert error.details == {}


def test_app_error_status_code_is_stored() -> None:
    error = AppError(
        code="NOT_FOUND",
        message="Not found.",
        status_code=404,
    )

    assert error.status_code == 404


def test_app_error_status_code_is_coerced_to_int() -> None:
    error = AppError(status_code="404")  # type: ignore[arg-type]

    assert error.status_code == 404
    assert isinstance(error.status_code, int)


def test_app_error_code_and_message_are_coerced_to_str() -> None:
    error = AppError(code=123, message=456)  # type: ignore[arg-type]

    assert error.code == "123"
    assert error.message == "456"


def test_app_error_details_none_becomes_empty_dict() -> None:
    error = AppError(details=None)

    assert error.details == {}


def test_app_error_details_dict_is_defensively_copied() -> None:
    details = {"field": "value"}
    error = AppError(details=details)

    error.details["field"] = "tampered"

    assert details == {"field": "value"}


def test_app_error_to_dict_returns_plain_types() -> None:
    error = AppError(
        code="CONFLICT",
        message="This item needs review because the server has changed.",
        status_code=409,
        details={"field": "grade"},
    )

    payload = error.to_dict()

    assert payload == {
        "code": "CONFLICT",
        "message": "This item needs review because the server has changed.",
        "status_code": 409,
        "details": {"field": "grade"},
    }


def test_app_error_to_dict_copies_details() -> None:
    error = AppError(details={"field": "value"})

    payload = error.to_dict()
    payload["details"]["field"] = "tampered"

    assert error.details == {"field": "value"}


def test_app_error_repr_contains_code_and_status() -> None:
    error = AppError(
        code="PERMISSION_DENIED",
        message="You do not have permission to do this.",
        status_code=403,
    )

    text = repr(error)

    assert "AppError" in text
    assert "PERMISSION_DENIED" in text
    assert "403" in text


def test_app_error_str_matches_message() -> None:
    error = AppError(message="Custom message.")

    assert str(error) == "Custom message."


def test_app_error_args_contain_message() -> None:
    error = AppError(message="Custom message.")

    assert error.args == ("Custom message.",)


def test_app_error_can_be_pickled_and_restored() -> None:
    error = AppError(
        code="SYNC_FAILED",
        message="Could not sync yet. We will retry.",
        status_code=503,
        details={"operation_id": "abc123"},
    )

    restored = pickle.loads(pickle.dumps(error))

    assert isinstance(restored, AppError)
    assert restored.code == error.code
    assert restored.message == error.message
    assert restored.status_code == error.status_code
    assert restored.details == error.details


def test_app_error_can_be_chained() -> None:
    original = ValueError("underlying failure")

    with pytest.raises(AppError) as exc_info:
        try:
            raise original
        except ValueError as caught:
            raise AppError(
                code="WRAPPED",
                message="Wrapped failure.",
                status_code=500,
            ) from caught

    assert exc_info.value.__cause__ is original


def test_app_error_is_exception_subclass() -> None:
    error = AppError()

    assert isinstance(error, Exception)


_SUBCLASS_CASES: list[tuple[type[AppError], str, int, str]] = [
    (
        NotFoundError,
        "not_found",
        404,
        "The requested item was not found.",
    ),
    (
        ConflictError,
        "conflict",
        409,
        "This item needs review because the server has changed.",
    ),
    (
        PermissionDeniedError,
        "permission_denied",
        403,
        "You do not have permission to do this.",
    ),
    (
        ValidationError,
        "validation_error",
        422,
        "Enter a valid value.",
    ),
    (
        UnauthenticatedError,
        "unauthenticated",
        401,
        "Please sign in again.",
    ),
    (
        IdempotencyConflictError,
        "idempotency_conflict",
        409,
        "This operation was already submitted.",
    ),
    (
        ServiceUnavailableError,
        "service_unavailable",
        503,
        "The service is temporarily unavailable.",
    ),
]


@pytest.mark.parametrize(
    ("cls", "expected_code", "expected_status", "expected_message"),
    _SUBCLASS_CASES,
)
def test_subclass_defaults(
    cls: type[AppError],
    expected_code: str,
    expected_status: int,
    expected_message: str,
) -> None:
    error = cls()
    assert error.code == expected_code
    assert error.status_code == expected_status
    assert error.message == expected_message


@pytest.mark.parametrize(
    ("cls", "expected_code", "expected_status", "expected_message"),
    _SUBCLASS_CASES,
)
def test_subclass_to_dict(
    cls: type[AppError],
    expected_code: str,
    expected_status: int,
    expected_message: str,
) -> None:
    error = cls()
    payload = error.to_dict()

    assert isinstance(payload, dict)
    assert payload == {
        "code": expected_code,
        "message": expected_message,
        "status_code": expected_status,
        "details": {},
    }


@pytest.mark.parametrize(
    ("cls", "_code", "_status", "_message"),
    _SUBCLASS_CASES,
)
def test_subclass_details_is_dict(
    cls: type[AppError],
    _code: str,
    _status: int,
    _message: str,
) -> None:
    error = cls(details={"field": "value"})

    assert isinstance(error.details, dict)
    assert error.details == {"field": "value"}


@pytest.mark.parametrize(
    ("cls", "_code", "_status", "_message"),
    _SUBCLASS_CASES,
)
def test_subclass_details_none_yields_empty_dict(
    cls: type[AppError],
    _code: str,
    _status: int,
    _message: str,
) -> None:
    error = cls(details=None)

    assert error.details == {}


@pytest.mark.parametrize(
    ("cls", "_code", "_status", "_message"),
    _SUBCLASS_CASES,
)
def test_subclass_message_override(
    cls: type[AppError],
    _code: str,
    _status: int,
    _message: str,
) -> None:
    error = cls(message="Custom override.")

    assert error.message == "Custom override."


@pytest.mark.parametrize(
    ("cls", "_code", "_status", "_message"),
    _SUBCLASS_CASES,
)
def test_subclass_inherits_app_error(
    cls: type[AppError],
    _code: str,
    _status: int,
    _message: str,
) -> None:
    error = cls()

    assert isinstance(error, AppError)
    assert isinstance(error, Exception)
