from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ttcs_db"
    DB_USER: str = "ttcs_app"
    DB_PASSWORD: str = ""
    DB_ADMIN_USER: str = "admin"
    DB_ADMIN_PASSWORD: str = ""
    DATABASE_URL_ENV: str | None = None
    DB_POOL_SIZE: int = 5
    DB_POOL_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 300

    APP_ENV: str = "development"
    SECRET_KEY: str = ""
    DEBUG: bool = False
    SESSION_TTL_MINUTES: int = 480
    SESSION_COOKIE_NAME: str = "__Host-session"
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 20
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://ttcs-frontend-staging.onrender.com",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        origins = (
            [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else v
        )
        # `allow_credentials=True` combined with a wildcard origin makes Starlette
        # echo the caller's Origin, which turns the CORS layer into an open door.
        if "*" in origins:
            raise ValueError(
                "ALLOWED_ORIGINS must not contain '*' because the API sends credentialed cookies"
            )
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(
                    f"ALLOWED_ORIGINS entry is not a valid origin: {origin!r}"
                )
        return origins

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        if self.SESSION_TTL_MINUTES < 1:
            raise ValueError("SESSION_TTL_MINUTES must be positive")
        if self.MAX_FAILED_LOGIN_ATTEMPTS < 1:
            raise ValueError("MAX_FAILED_LOGIN_ATTEMPTS must be positive")
        if self.ACCOUNT_LOCK_MINUTES < 1:
            raise ValueError("ACCOUNT_LOCK_MINUTES must be positive")
        if self.SESSION_COOKIE_SAMESITE == "none" and not self.SESSION_COOKIE_SECURE:
            raise ValueError("SameSite=None cookies require SESSION_COOKIE_SECURE=true")
        if self.APP_ENV != "development" and not self.SESSION_COOKIE_SECURE:
            raise ValueError(
                "SESSION_COOKIE_SECURE must stay enabled outside development"
            )
        if self.DB_USER == self.DB_ADMIN_USER:
            raise ValueError(
                "DB_USER and DB_ADMIN_USER must be distinct so the application "
                "never runs with a migration/admin database role"
            )
        if self.APP_ENV != "development" and len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must contain at least 32 characters outside development"
            )
        if self.APP_ENV != "development" and self.DEBUG:
            raise ValueError("DEBUG must be disabled outside development")
        return self

    @property
    def DATABASE_URL(self) -> URL | str:
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+psycopg://", 1)
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return URL.create(
            "postgresql+psycopg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def MIGRATION_DATABASE_URL(self) -> URL | str:
        if self.DATABASE_URL_ENV:
            return self.DATABASE_URL
        return URL.create(
            "postgresql+psycopg",
            username=self.DB_ADMIN_USER,
            password=self.DB_ADMIN_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )


settings = Settings()
