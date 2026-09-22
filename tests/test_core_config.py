from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from app.core.config import MAX_TOTAL_CONNECTIONS, Settings, get_settings

VALID_URL = "postgresql+psycopg://user:pass@localhost:5432/farmer"
VALID_JWT_SECRET = "a_valid_secret_key_that_is_at_least_32_characters_long"


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("JWT_SECRET_KEY", VALID_JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_loads_with_valid_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)

    settings = Settings(_env_file=None)

    assert settings.app_name == "Farmer Backend"
    assert settings.environment == "development"
    assert settings.database_url == VALID_URL


def test_environment_variable_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_NAME", "Custom")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.app_name == "Custom"


def test_pool_defaults_are_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)

    settings = Settings(_env_file=None)

    assert settings.db_pool_size == 10
    assert settings.db_max_overflow == 20
    assert settings.db_pool_timeout == 30
    assert settings.db_pool_recycle == 1800
    assert settings.db_sql_echo is False


def test_pool_values_come_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("DB_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "15")
    monkeypatch.setenv("DB_POOL_RECYCLE", "600")
    monkeypatch.setenv("DB_SQL_ECHO", "true")

    settings = Settings(_env_file=None)

    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 5
    assert settings.db_pool_timeout == 15
    assert settings.db_pool_recycle == 600
    assert settings.db_sql_echo is True


def test_sql_echo_defaults_to_false_in_every_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for environment in ("development", "staging", "production"):
        monkeypatch.setenv("DATABASE_URL", VALID_URL)
        monkeypatch.setenv("ENVIRONMENT", environment)
        monkeypatch.delenv("DB_SQL_ECHO", raising=False)

        settings = Settings(_env_file=None)

        assert settings.db_sql_echo is False


def test_rejects_missing_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_sync_postgresql_scheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@localhost:5432/db",
    )

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "postgresql+psycopg://" in str(exc_info.value)


def test_rejects_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("ENVIRONMENT", "staging-west")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_pool_budget_over_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("DB_POOL_SIZE", "80")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "40")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert str(MAX_TOTAL_CONNECTIONS) in str(exc_info.value)


def test_accepts_pool_budget_at_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("DB_POOL_SIZE", "80")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "20")

    settings = Settings(_env_file=None)

    assert settings.db_pool_size + settings.db_max_overflow == MAX_TOTAL_CONNECTIONS


def test_rejects_zero_pool_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("DB_POOL_SIZE", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_negative_max_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("DB_MAX_OVERFLOW", "-1")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_is_frozen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)

    settings = Settings(_env_file=None)

    with pytest.raises((TypeError, ValidationError)):
        attr = "database_url"
        setattr(
            settings,
            attr,
            "postgresql+psycopg://other:other@localhost:5432/farmer",
        )


def test_get_settings_is_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)

    assert get_settings() is get_settings()


def test_get_settings_cache_can_be_cleared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    first = get_settings()

    get_settings.cache_clear()

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://other:other@localhost:5432/farmer",
    )
    second = get_settings()

    assert first is not second
    assert first.database_url != second.database_url


def test_jwt_defaults_and_explicit_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", VALID_JWT_SECRET)

    settings = Settings(_env_file=None)
    assert settings.jwt_secret_key == VALID_JWT_SECRET
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30

    secret = "custom_secret_key_at_least_32_characters_long"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    custom_settings = Settings(_env_file=None)
    assert custom_settings.jwt_secret_key == secret
    assert custom_settings.access_token_expire_minutes == 60


def test_jwt_secret_key_min_length_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", "too_short_secret")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_rejects_missing_jwt_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_allowed_origins_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    settings = Settings(_env_file=None)
    assert settings.cors_allowed_origins == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_cors_allowed_origins_json_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["http://example.com", "https://app.example.com"]',
    )
    settings = Settings(_env_file=None)
    assert settings.cors_allowed_origins == [
        "http://example.com",
        "https://app.example.com",
    ]


def test_cors_allowed_origins_rejects_wildcard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", VALID_URL)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["*"]')
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
