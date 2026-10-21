from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IntegrityAlert(Base):
    """Append-only record raised when a lot's event chain is found broken.

    The scheduled scanner raises one alert per newly detected breakage, so the
    administrator view can tell when the problem was found and not only that
    the latest check failed.
    """

    __tablename__ = "integrity_alerts"
    __table_args__ = (
        CheckConstraint("issue_count >= 1", name="ck_integrity_alerts_issue_count"),
        CheckConstraint("checked_events >= 0", name="ck_integrity_alerts_event_count"),
        Index("ix_integrity_alerts_detected_at", "detected_at"),
        Index("ix_integrity_alerts_lot_detected", "lot_id", "detected_at"),
        Index(
            "ix_integrity_alerts_organization_detected",
            "organization_id",
            "detected_at",
        ),
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
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
    first_invalid_sequence: Mapped[int | None] = mapped_column(Integer)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_events: Mapped[int] = mapped_column(Integer, nullable=False)
