from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]
AsyncScheme = str

MAX_TOTAL_CONNECTIONS = 100


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )

    app_name: str = Field(
        default="Farmer Backend",
        min_length=1,
        max_length=120,
    )
    environment: Environment = "development"
    database_url: str = Field(min_length=1)

    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_pool_timeout: int = Field(default=30, ge=1, le=300)
    db_pool_recycle: int = Field(default=1800, ge=60, le=86400)
    db_sql_echo: bool = False

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    @field_validator("cors_allowed_origins")
    @classmethod
    def _validate_cors_origins(cls, value: list[str]) -> list[str]:
        for origin in value:
            if origin == "*":
                raise ValueError(
                    "Wildcard '*' origin is not permitted when credentials are enabled"
                )
        return value

    @field_validator("database_url")
    @classmethod
    def _require_async_driver(cls, value: str) -> str:
        scheme = value.split("://", 1)[0]
        if scheme != "postgresql+psycopg":
            raise ValueError(
                "database_url must use the postgresql+psycopg:// scheme "
                "for SQLAlchemy async support"
            )
        return value

    @model_validator(mode="after")
    def _validate_pool_budget(self) -> "Settings":
        total = self.db_pool_size + self.db_max_overflow

        if total > MAX_TOTAL_CONNECTIONS:
            raise ValueError(
                f"db_pool_size + db_max_overflow = {total} exceeds "
                f"MAX_TOTAL_CONNECTIONS = {MAX_TOTAL_CONNECTIONS}"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
