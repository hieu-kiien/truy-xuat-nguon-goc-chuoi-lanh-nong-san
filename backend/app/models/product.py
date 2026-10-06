from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_products_name_nonblank"),
        CheckConstraint(
            "unit IN ('kg', 'tấn', 'thùng')",
            name="ck_products_unit_supported",
        ),
        Index("uq_products_name_ci", func.lower(text("name")), unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
