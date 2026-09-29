from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.orm.session import SessionTransaction

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(SessionLocal, "after_begin")
def set_database_tenant_context(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    settings = {
        "app.current_organization": session.info.get("organization_id"),
        "app.current_user_id": session.info.get("user_id"),
        "app.current_role": session.info.get("role"),
        "app.session_token_hash": session.info.get("session_token_hash"),
    }
    for name, value in settings.items():
        if value is not None:
            connection.execute(
                text("SELECT set_config(:setting_name, :setting_value, true)"),
                {"setting_name": name, "setting_value": str(value)},
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
        db.close()
