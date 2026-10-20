from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

NOTIFICATION_KINDS = (
    "handover_pending",
    "recall_affected",
    "cold_chain_violation",
)


class Notification(Base):
    """One notification addressed to a single user (N3-56).

    Rows are produced by the notification service, never by the interface.
    ``source_key`` keeps the notification stable so the same underlying item
    never produces two rows for the same recipient.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('handover_pending', 'recall_affected', 'cold_chain_violation')",
            name="ck_notifications_kind",
        ),
        CheckConstraint(
            "length(btrim(title)) > 0", name="ck_notifications_title_nonblank"
        ),
        CheckConstraint(
            "length(btrim(link_path)) > 0", name="ck_notifications_link_nonblank"
        ),
        UniqueConstraint(
            "recipient_user_id",
            "source_key",
            name="uq_notifications_recipient_source",
        ),
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index(
            "ix_notifications_recipient_unread",
            "recipient_user_id",
            unique=False,
            postgresql_where=text("read_at IS NULL"),
        ),
        Index("ix_notifications_lot_id", "lot_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_path: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("lots.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
