"""Models for recall orders, affected recall lots, and append-only recall confirmations."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

DEFAULT_RECALL_REASON = (
    "Lô hàng thuộc diện thu hồi khẩn cấp để kiểm tra an toàn thực phẩm."
)


class RecallOrder(Base):
    __tablename__ = "recall_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'completed')",
            name="ck_recall_orders_status_supported",
        ),
        CheckConstraint(
            "length(btrim(recall_code)) > 0",
            name="ck_recall_orders_code_nonblank",
        ),
        CheckConstraint(
            "length(btrim(reason)) >= 20",
            name="ck_recall_orders_reason_min_length",
        ),
        Index("ix_recall_orders_root_lot_id", "root_lot_id"),
        Index("ix_recall_orders_status", "status"),
        Index("ix_recall_orders_opened_by_org_id", "opened_by_organization_id"),
        Index(
            "uq_recall_orders_open_root_lot",
            "root_lot_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    recall_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    root_lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "lots.id",
            name="fk_recall_orders_root_lot_id_lots",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    opened_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_recall_orders_opened_by_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    opened_by_organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_recall_orders_opened_by_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="open", server_default=text("'open'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __init__(self, **kwargs: Any) -> None:
        if "code" in kwargs and "recall_code" not in kwargs:
            kwargs["recall_code"] = kwargs.pop("code")
        else:
            kwargs.pop("code", None)
        if "organization_id" in kwargs and "opened_by_organization_id" not in kwargs:
            kwargs["opened_by_organization_id"] = kwargs.pop("organization_id")
        else:
            kwargs.pop("organization_id", None)
        if "created_by_user_id" in kwargs and "opened_by_user_id" not in kwargs:
            kwargs["opened_by_user_id"] = kwargs.pop("created_by_user_id")
        else:
            kwargs.pop("created_by_user_id", None)
        note = kwargs.pop("note", None)
        if "reason" not in kwargs or not kwargs["reason"]:
            candidate = (note or "").strip()
            kwargs["reason"] = (
                candidate if len(candidate) >= 20 else DEFAULT_RECALL_REASON
            )
        super().__init__(**kwargs)

    # Helper aliases
    @property
    def code(self) -> str:
        return self.recall_code

    @property
    def organization_id(self) -> UUID:
        return self.opened_by_organization_id

    @property
    def created_by_user_id(self) -> UUID:
        return self.opened_by_user_id

    @property
    def note(self) -> str:
        return self.reason

    @property
    def root_lot_item(self) -> Any:
        return getattr(self, "_root_lot_item", None)

    @root_lot_item.setter
    def root_lot_item(self, value: Any) -> None:
        self._root_lot_item = value

    @property
    def confirmations_read(self) -> Any:
        return getattr(self, "_confirmations_read", [])

    @confirmations_read.setter
    def confirmations_read(self, value: Any) -> None:
        self._confirmations_read = value

    # Relationships
    root_lot = relationship("Lot", foreign_keys=[root_lot_id])
    opened_by_user = relationship("User", foreign_keys=[opened_by_user_id])
    opened_by_organization = relationship(
        "Organization", foreign_keys=[opened_by_organization_id]
    )
    lot_entries = relationship(
        "RecallOrderLot",
        back_populates="recall_order",
        cascade="all, delete-orphan",
    )
    confirmations = relationship(
        "RecallConfirmation",
        back_populates="recall_order",
    )


class RecallOrderLot(Base):
    __tablename__ = "recall_order_lots"
    __table_args__ = (
        UniqueConstraint(
            "recall_order_id",
            "lot_id",
            name="uq_recall_order_lots_order_lot",
        ),
        Index("ix_recall_order_lots_recall_order_id", "recall_order_id"),
        Index("ix_recall_order_lots_lot_id", "lot_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    recall_order_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "recall_orders.id",
            name="fk_recall_order_lots_recall_order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_recall_order_lots_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    lot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "lots.id",
            name="fk_recall_order_lots_lot_id_lots",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    incident_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    recall_order = relationship("RecallOrder", back_populates="lot_entries")
    lot = relationship("Lot", foreign_keys=[lot_id])


class RecallConfirmation(Base):
    __tablename__ = "recall_confirmations"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(note)) > 0",
            name="ck_recall_confirmations_note_nonblank",
        ),
        UniqueConstraint(
            "recall_order_id",
            "organization_id",
            name="uq_recall_confirmations_order_org",
        ),
        Index("ix_recall_confirmations_recall_order_id", "recall_order_id"),
        Index("ix_recall_confirmations_organization_id", "organization_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    recall_order_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "recall_orders.id",
            name="fk_recall_confirmations_recall_order_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_recall_confirmations_org_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    confirmed_by_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_recall_confirmations_user_id_users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    recall_order = relationship("RecallOrder", back_populates="confirmations")
    organization = relationship("Organization", foreign_keys=[organization_id])
    confirmed_by_user = relationship("User", foreign_keys=[confirmed_by_user_id])
