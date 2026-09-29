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
    organization_id = session.info.get("organization_id")
    if organization_id:
        connection.execute(
            text(
                "SELECT set_config('app.current_organization', "
                ":organization_id, true)"
            ),
            {"organization_id": organization_id},
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
