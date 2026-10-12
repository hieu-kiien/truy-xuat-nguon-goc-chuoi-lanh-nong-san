"""Immutable identity snapshots remain valid after account removal."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success','denied','error')", name="ck_audit_outcome"
        ),
        CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_audit_status"),
        CheckConstraint("length(action) > 0", name="ck_audit_action"),
        Index("ix_audit_recorded_id", "recorded_at", "id"),
        Index("ix_audit_actor_recorded", "actor_user_id", "recorded_at"),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    actor_name: Mapped[str | None] = mapped_column(String(200))
    actor_authenticated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    organization_name: Mapped[str | None] = mapped_column(String(200))
    client_ip: Mapped[str | None] = mapped_column(String(45))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64))
