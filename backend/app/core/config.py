from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ttcs_db"
    DB_USER: str = "admin"
    DB_PASSWORD: str = "password123"

    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    SESSION_TTL_MINUTES: int = 480
    SESSION_COOKIE_NAME: str = "__Host-session"
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
