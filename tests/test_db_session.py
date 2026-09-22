from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import session as session_module

TEST_URL = "postgresql+psycopg://user:pass@localhost:5432/farmer_test"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    monkeypatch.setenv(
        "JWT_SECRET_KEY", "a_valid_secret_key_that_is_at_least_32_characters_long"
    )
    monkeypatch.delenv("DB_SQL_ECHO", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def _dispose(_env: Iterator[None]) -> AsyncIterator[None]:
    yield
    await session_module.dispose_engine()


def test_get_engine_returns_singleton() -> None:
    first = session_module.get_engine()
    second = session_module.get_engine()

    assert first is second


def test_get_session_factory_returns_singleton() -> None:
    first = session_module.get_session_factory()
    second = session_module.get_session_factory()

    assert first is second


async def test_session_factory_produces_async_session() -> None:
    factory = session_module.get_session_factory()
    session = factory()

    try:
        assert isinstance(session, AsyncSession)
    finally:
        await session.close()


async def test_engine_uses_configured_pool_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_POOL_SIZE", "4")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "6")
    get_settings.cache_clear()

    await session_module.dispose_engine()

    engine = session_module.get_engine()
    pool = engine.pool

    from sqlalchemy.pool import QueuePool

    assert isinstance(pool, QueuePool)
    assert pool.size() == 4


async def test_engine_does_not_enable_sql_echo_by_default() -> None:
    await session_module.dispose_engine()

    engine = session_module.get_engine()

    assert engine.echo is False


async def test_get_db_session_yields_session() -> None:
    sessions: list[AsyncSession] = []

    async for session in session_module.get_db_session():
        sessions.append(session)

    assert len(sessions) == 1
    assert isinstance(sessions[0], AsyncSession)


async def test_get_db_session_rolls_back_when_exception_is_thrown_into_generator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback_called = False
    original_rollback = AsyncSession.rollback

    async def tracking_rollback(self: AsyncSession) -> None:
        nonlocal rollback_called
        rollback_called = True
        await original_rollback(self)

    monkeypatch.setattr(
        AsyncSession,
        "rollback",
        tracking_rollback,
    )

    from collections.abc import AsyncGenerator
    from typing import cast

    generator = cast(AsyncGenerator[AsyncSession], session_module.get_db_session())
    session = await generator.__anext__()

    assert isinstance(session, AsyncSession)

    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    assert rollback_called is True


async def test_dispose_engine_clears_singletons() -> None:
    session_module.get_engine()
    session_module.get_session_factory()

    await session_module.dispose_engine()

    assert session_module._engine is None
    assert session_module._session_factory is None
