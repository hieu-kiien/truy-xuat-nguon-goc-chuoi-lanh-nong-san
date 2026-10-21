from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailOutbox(Base):
    """Record of an outbound message (N3-57, N3-30).

    The row is written before the message is handed to the transport, so a
    failed delivery still leaves evidence and can be retried. ``status`` tells
    what happened: ``sent`` when an SMTP server accepted the message,
    ``recorded`` when no SMTP server is configured, ``failed`` when every
    attempt was rejected.
    """

    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('sent', 'recorded', 'failed')", name="ck_email_outbox_status"
        ),
        CheckConstraint("attempts >= 0", name="ck_email_outbox_attempts_nonnegative"),
        CheckConstraint(
            "length(btrim(recipient_email)) > 0",
            name="ck_email_outbox_recipient_nonblank",
        ),
        Index("ix_email_outbox_organization_created", "organization_id", "created_at"),
        Index("ix_email_outbox_kind", "kind"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    related_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="recorded",
        server_default=text("'recorded'"),
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
