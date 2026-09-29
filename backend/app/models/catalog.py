from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "min_temperature_c IS NULL OR max_temperature_c IS NULL OR "
            "min_temperature_c <= max_temperature_c",
            name="ck_products_temperature_range",
        ),
        UniqueConstraint("id", "organization_id", name="uq_products_id_organization"),
        Index("ix_products_organization_created", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    min_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    max_temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
