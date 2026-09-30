from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.orm.session import SessionTransaction

from app.core.config import settings

# Pooled connections are long-lived and are frequently recycled by the
# database or the platform (Render's free plan spins Postgres down), so
# `pool_pre_ping` is required to avoid handing dead sockets to requests.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Session-scoped GUCs propagated on every transaction begin. These are pushed
# with `is_local=True` (SET LOCAL) so a tenant context can never survive the
# transaction and leak into the next request that reuses the pooled connection.
# `app.login_email` is included so a post-commit statement in the login flow
# still sees the row it is working on.
TENANT_CONTEXT_SETTINGS = {
    "app.current_organization": "organization_id",
    "app.current_user_id": "user_id",
    "app.current_role": "role",
    "app.session_token_hash": "session_token_hash",
    "app.login_email": "login_email",
}


@event.listens_for(SessionLocal, "after_begin")
def set_database_tenant_context(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    for setting_name, info_key in TENANT_CONTEXT_SETTINGS.items():
        value = session.info.get(info_key)
        if value is not None:
            connection.execute(
                text("SELECT set_config(:setting_name, :setting_value, true)"),
                {"setting_name": setting_name, "setting_value": str(value)},
            )


class Base(DeclarativeBase):
    """Base class cho tất cả SQLAlchemy models trong dự án."""

    pass


def get_db():
    """Dependency injection: cung cấp DB session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Never let a failed request leave an open transaction holding row
        # locks, and never let tenant context outlive the request.
        db.rollback()
        db.close()
