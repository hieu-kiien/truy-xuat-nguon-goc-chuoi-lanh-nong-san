from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LotRelation(Base):
    """Immutable quantity transferred from a parent to a newly created lot."""

    __tablename__ = "lot_relations"
    __table_args__ = (
        CheckConstraint(
            "parent_lot_id <> child_lot_id", name="ck_lot_relations_not_self"
        ),
        CheckConstraint(
            "quantity > 0 AND quantity < 'Infinity'::numeric",
            name="ck_lot_relations_quantity",
        ),
        CheckConstraint(
            "operation IN ('split', 'merge')", name="ck_lot_relations_operation"
        ),
        UniqueConstraint("parent_lot_id", "child_lot_id", name="uq_lot_relations_edge"),
        Index("ix_lot_relations_child", "child_lot_id"),
        Index("ix_lot_relations_organization", "organization_id"),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    parent_lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False
    )
    child_lot_id: Mapped[UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    operation: Mapped[str] = mapped_column(String(8), nullable=False)
