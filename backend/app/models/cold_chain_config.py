"""Per-product cold chain temperature threshold configuration (N3-62).

Admins configure an upper threshold, a lower threshold, and a confirmation
delay per product type so different goods (e.g. leafy greens vs frozen meat)
are not monitored with one shared number.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.product import Product


class ProductColdChainConfig(Base):
    """A shared, admin-managed cold chain profile attached to one product."""

    __tablename__ = "product_cold_chain_configs"
    __table_args__ = (
        CheckConstraint(
            "min_temp_celsius < max_temp_celsius",
            name="ck_cold_chain_configs_temp_range",
        ),
        CheckConstraint(
            "min_temp_celsius >= -50 AND max_temp_celsius <= 80",
            name="ck_cold_chain_configs_temp_bounds",
        ),
        CheckConstraint(
            "delay_minutes >= 1 AND delay_minutes <= 1440",
            name="ck_cold_chain_configs_delay_range",
        ),
        UniqueConstraint("product_id", name="uq_cold_chain_configs_product"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "products.id",
            name="fk_cold_chain_configs_product_id_products",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    min_temp_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_temp_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    delay_minutes: Mapped[int] = mapped_column(nullable=False)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_cold_chain_configs_updated_by_user_id_users",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    # Relationships
    product: Mapped[Product] = relationship("Product", lazy="joined")

    @property
    def product_name(self) -> str:
        return self.product.name
