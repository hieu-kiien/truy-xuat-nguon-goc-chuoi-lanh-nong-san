from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_lots_name_nonblank"),
        ForeignKeyConstraint(
            ["farm_id", "organization_id"],
            ["farms.id", "farms.organization_id"],
            name="fk_lots_farm_same_organization",
            ondelete="RESTRICT",
        ),
        Index("ix_lots_organization_id", "organization_id"),
        Index("ix_lots_farm_id", "farm_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_lots_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    farm_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
