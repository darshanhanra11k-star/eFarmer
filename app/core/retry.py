import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

import psycopg.errors
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)

TRANSIENT_SQLSTATES = frozenset({"40P01"})


def is_transient_db_error(exc: Exception) -> bool:
    """Detect if an exception is a transient database concurrency error.

    Under READ COMMITTED isolation level, only deadlock_detected (40P01)
    is transient and retryable.
    """
    if isinstance(exc, psycopg.errors.DeadlockDetected):
        return True

    if isinstance(exc, DBAPIError):
        orig = getattr(exc, "orig", None)
        if orig is not None:
            if isinstance(orig, psycopg.errors.DeadlockDetected):
                return True
            sqlstate = getattr(orig, "sqlstate", None)
            if sqlstate in TRANSIENT_SQLSTATES:
                return True

    return False


async def run_with_retry[T](
    session: AsyncSession,
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.05,
    max_delay: float = 0.5,
) -> T:
    """Execute a transactional operation with bounded retries on transient DB errors.

    Guarantees:
    - Same request-scoped AsyncSession is used across attempts.
    - await session.rollback() is called before each retry.
    - Full operation is re-executed from scratch on each attempt.
    - Non-transient errors (validation, conflict, not found, etc.) are NOT retried.
    - When retries are exhausted, raises ServiceUnavailableError (HTTP 503).
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt < max_attempts and is_transient_db_error(exc):
                logger.warning(
                    "Transient database conflict on attempt %d/%d; "
                    "rolling back and retrying: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                await session.rollback()
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                jitter = random.uniform(0, delay * 0.25)
                await asyncio.sleep(delay + jitter)
                continue
            elif attempt >= max_attempts and is_transient_db_error(exc):
                logger.error(
                    "Transient database conflicts exhausted after %d attempts: %s",
                    max_attempts,
                    exc,
                )
                await session.rollback()
                raise ServiceUnavailableError(
                    message=(
                        "Service is temporarily unavailable due to concurrent "
                        "transaction conflicts. Please retry."
                    ),
                    details={"transient_error": "deadlock_detected"},
                ) from None

            # For non-transient exceptions, ensure session is rolled back
            await session.rollback()
            raise

    raise RuntimeError("Retry loop unexpectedly terminated without result")
