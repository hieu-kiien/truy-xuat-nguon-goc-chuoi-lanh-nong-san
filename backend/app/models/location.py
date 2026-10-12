from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Location(Base):
    """A store or warehouse owned by a distribution organization."""

    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_locations_id_organization"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_locations_name_nonblank"),
        CheckConstraint(
            "length(btrim(address)) > 0", name="ck_locations_address_nonblank"
        ),
        Index("ix_locations_organization_id", "organization_id"),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
