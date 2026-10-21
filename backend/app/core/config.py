from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _normalize_postgres_url(value: str) -> URL:
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    elif value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    return make_url(value)


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
    MIGRATION_DATABASE_URL_ENV: str | None = None

    APP_ENV: str = "production"
    DEBUG: bool = False
    DEMO_PASSWORD: str | None = None
    LOGIN_LOCK_MINUTES: int = Field(default=15, ge=1, le=1440)
    SESSION_TTL_MINUTES: int = Field(default=480, ge=1, le=10080)
    HANDOVER_OVERDUE_HOURS: int = Field(default=48, ge=1, le=8760)
    PUBLIC_TRACE_CACHE_TTL_SECONDS: int = Field(default=60, ge=0, le=3600)
    PUBLIC_TRACE_RATE_LIMIT_CODES: int = Field(default=30, ge=1, le=1000)
    PUBLIC_TRACE_RATE_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600)
    SESSION_COOKIE_NAME: str = "__Host-session"
    SESSION_COOKIE_SAMESITE: str = "none"
    SESSION_COOKIE_SECURE: bool = True
    # Outbound e-mail (N3-57, N3-30). When SMTP_HOST is empty the messages are
    # only written to the outbox, which keeps the evidence without a server.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@agrochain.local"
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 15
    EMAIL_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=5)
    EMAIL_RETRY_DELAY_SECONDS: float = Field(default=1.0, ge=0.0, le=30.0)
    PUBLIC_APP_URL: str = "http://localhost:5173"
    # Off-application-server backup store (N3-160). Any S3-compatible bucket
    # works: AWS S3, Backblaze B2, Cloudflare R2, MinIO. When the bucket name
    # is empty the nightly job only keeps the dump in the CI artifact, which
    # is not a place to recover from after the artifact expires.
    BACKUP_EXTERNAL_BUCKET: str = ""
    BACKUP_EXTERNAL_ENDPOINT: str = ""
    BACKUP_EXTERNAL_REGION: str = "auto"
    BACKUP_EXTERNAL_ACCESS_KEY_ID: str = ""
    BACKUP_EXTERNAL_SECRET_ACCESS_KEY: str = ""
    BACKUP_EXTERNAL_PREFIX: str = "agrochain"
    BACKUP_EXTERNAL_RETENTION_DAYS: int = Field(default=90, ge=1, le=3650)
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://ttcs-frontend-staging.onrender.com",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        else:
            origins = value
        if "*" in origins:
            raise ValueError("ALLOWED_ORIGINS cannot include a wildcard origin")
        return origins

    @model_validator(mode="after")
    def require_separate_database_roles(self) -> "Settings":
        if self.DB_USER == self.DB_ADMIN_USER:
            raise ValueError("DB_USER and DB_ADMIN_USER must be different")
        return self

    @property
    def smtp_configured(self) -> bool:
        """Tell whether a real transport is configured for outbound e-mail.

        Without a host the messages only reach the outbox table, so the
        staging environment cannot claim to have sent anything (N3-160).
        """
        return bool(self.SMTP_HOST.strip())

    @property
    def backup_external_store_configured(self) -> bool:
        """Tell whether dumps can leave the CI artifact store."""
        return bool(self.BACKUP_EXTERNAL_BUCKET.strip())

    def validate_backup_external_store(self) -> None:
        """Fail when the external backup store is only half configured.

        A bucket without credentials silently drops every dump, so the
        misconfiguration has to be loud instead of quiet.
        """
        if not self.backup_external_store_configured:
            return
        missing = [
            name
            for name in (
                "BACKUP_EXTERNAL_ACCESS_KEY_ID",
                "BACKUP_EXTERNAL_SECRET_ACCESS_KEY",
            )
            if not getattr(self, name).strip()
        ]
        if missing:
            raise ValueError(
                "Thiếu cấu hình kho bản sao lưu ngoài: " + ", ".join(missing)
            )

    def validate_runtime(self, *, migrate: bool = False) -> None:
        """Fail before serving traffic, without including credential values."""
        if not self.DATABASE_URL.password:
            raise ValueError("Thiếu DB_PASSWORD hoặc DATABASE_URL_ENV có mật khẩu")
        if self.DATABASE_URL.username == self.DB_ADMIN_USER:
            raise ValueError(
                "DATABASE_URL_ENV phải dùng DB_USER, không dùng DB_ADMIN_USER"
            )
        if migrate and not self.MIGRATION_DATABASE_URL.password:
            raise ValueError("Thiếu DB_ADMIN_PASSWORD hoặc MIGRATION_DATABASE_URL_ENV")

    @property
    def DATABASE_URL(self) -> URL:
        if self.DATABASE_URL_ENV:
            url = _normalize_postgres_url(self.DATABASE_URL_ENV)
            if self.DB_PASSWORD and url.username != self.DB_USER:
                return url.set(username=self.DB_USER, password=self.DB_PASSWORD)
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
    def MIGRATION_DATABASE_URL(self) -> URL:
        if self.MIGRATION_DATABASE_URL_ENV:
            url = _normalize_postgres_url(self.MIGRATION_DATABASE_URL_ENV)
            if self.DB_ADMIN_PASSWORD and url.username != self.DB_ADMIN_USER:
                return url.set(
                    username=self.DB_ADMIN_USER,
                    password=self.DB_ADMIN_PASSWORD,
                )
            return url

        if self.DATABASE_URL_ENV:
            if self.DB_ADMIN_PASSWORD:
                url = _normalize_postgres_url(self.DATABASE_URL_ENV)
                return url.set(
                    username=self.DB_ADMIN_USER,
                    password=self.DB_ADMIN_PASSWORD,
                )
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
