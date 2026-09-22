from unittest.mock import AsyncMock

import psycopg.errors
import pytest
from sqlalchemy.exc import OperationalError

from app.core.exceptions import ConflictError, ServiceUnavailableError
from app.core.retry import is_transient_db_error, run_with_retry


@pytest.mark.asyncio
async def test_deadlock_automatic_retry_success() -> None:
    """Test that a transient 40P01 deadlock_detected triggers rollback and retry."""
    session = AsyncMock()
    attempts = 0

    orig_deadlock = psycopg.errors.DeadlockDetected("deadlock detected")
    deadlock_exc = OperationalError("SELECT ... FOR UPDATE", {}, orig_deadlock)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise deadlock_exc
        return "success"

    result = await run_with_retry(
        session,
        operation,
        max_attempts=3,
        base_delay=0.001,
        max_delay=0.01,
    )

    assert result == "success"
    assert attempts == 2
    # Verify session.rollback() was called before retry
    assert session.rollback.await_count == 1


@pytest.mark.asyncio
async def test_deadlock_retry_exhaustion_raises_service_unavailable() -> None:
    """Test that exhausting 3 deadlock attempts raises ServiceUnavailableError (503)."""
    session = AsyncMock()
    attempts = 0

    orig_deadlock = psycopg.errors.DeadlockDetected("deadlock detected")
    deadlock_exc = OperationalError("SELECT ... FOR UPDATE", {}, orig_deadlock)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise deadlock_exc

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await run_with_retry(
            session,
            operation,
            max_attempts=3,
            base_delay=0.001,
            max_delay=0.01,
        )

    assert attempts == 3
    assert exc_info.value.status_code == 503
    assert session.rollback.await_count == 3


@pytest.mark.asyncio
async def test_non_transient_error_is_not_retried() -> None:
    """Test that non-transient domain errors (ConflictError) fail immediately."""
    session = AsyncMock()
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ConflictError(message="Duplicate entry")

    with pytest.raises(ConflictError):
        await run_with_retry(
            session,
            operation,
            max_attempts=3,
            base_delay=0.001,
            max_delay=0.01,
        )

    assert attempts == 1
    # Verify rollback was called for clean cleanup
    assert session.rollback.await_count == 1


def test_is_transient_db_error_detection() -> None:
    """Verify transient error detection logic for PostgreSQL driver exceptions."""
    # 40P01 is transient
    deadlock_orig = psycopg.errors.DeadlockDetected("deadlock")
    deadlock_sa = OperationalError("stmt", {}, deadlock_orig)
    assert is_transient_db_error(deadlock_sa) is True
    assert is_transient_db_error(deadlock_orig) is True

    # Unique violation (23505) is NOT transient
    uniq_orig = psycopg.errors.UniqueViolation("duplicate")
    uniq_sa = OperationalError("stmt", {}, uniq_orig)
    assert is_transient_db_error(uniq_sa) is False
    assert is_transient_db_error(uniq_orig) is False

    # Standard exceptions are NOT transient
    assert is_transient_db_error(ValueError("bad value")) is False
