from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IntegrityCheck(Base):
    """Append-only audit record for a lot event-chain verification."""

    __tablename__ = "integrity_checks"
    __table_args__ = (
        CheckConstraint("checked_events >= 0", name="ck_integrity_checks_event_count"),
        Index("ix_integrity_checks_lot_checked", "lot_id", "checked_at"),
        Index("ix_integrity_checks_organization_checked", "organization_id", "checked_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checked_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    valid: Mapped[bool] = mapped_column(nullable=False)
    checked_events: Mapped[int] = mapped_column(Integer, nullable=False)
    first_invalid_sequence: Mapped[int | None] = mapped_column(Integer)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
