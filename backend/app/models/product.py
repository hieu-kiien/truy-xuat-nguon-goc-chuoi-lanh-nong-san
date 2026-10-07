import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductUnit(enum.StrEnum):
    KG = "kg"
    TAN = "tấn"
    THUNG = "thùng"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_products_name_nonblank"),
        CheckConstraint("price >= 0", name="ck_products_price_positive"),
        UniqueConstraint("name", name="uq_product_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[ProductUnit] = mapped_column(
        ENUM(
            ProductUnit,
            name="product_unit",
            values_callable=lambda enum_type: [unit.value for unit in enum_type],
        ),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    quantity: Mapped[int | None] = mapped_column(nullable=True, default=0)
