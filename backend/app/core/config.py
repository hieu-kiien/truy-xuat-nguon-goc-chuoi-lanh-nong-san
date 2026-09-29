from sqlalchemy.engine import URL
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    SESSION_TTL_MINUTES: int = 480
    SESSION_COOKIE_NAME: str = "__Host-session"
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://ttcs-frontend-staging.onrender.com",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

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
