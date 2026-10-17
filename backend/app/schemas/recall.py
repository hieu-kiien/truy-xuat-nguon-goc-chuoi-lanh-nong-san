from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.location import LocationRead


class RecallLotItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_code: str | None = None
    name: str
    tier: int
    status: str
    is_multi_source_merge: bool = False
    organization_id: UUID | None = None
    current_holder_organization_id: UUID | None = None
    current_holder_organization_name: str | None = None
    holder_org_type: str | None = None
    current_location_id: UUID | None = None
    current_location: LocationRead | None = None
    quantity: Decimal | None = None
    remaining_quantity: Decimal = Decimal("0.000")
    consumed_quantity: Decimal = Decimal("0.000")
    recoverable_quantity: Decimal = Decimal("0.000")
    unit: str | None = None
    harvested_on: date | None = None
    historical_only: bool = False
    parent_lot_ids: list[UUID] = []


class RecallSummary(BaseModel):
    root_lot_id: UUID
    root_lot_code: str | None = None
    root_lot_name: str
    initial_quantity: Decimal | None = None
    unit: str | None = None
    total_affected_lots: int
    total_descendants_count: int
    total_recoverable_kg: Decimal
    total_consumed_kg: Decimal
    involved_organizations_count: int
    involved_organizations: list[str]
    has_multi_source_merge: bool
    has_consumed_lot: bool


class RecallReport(BaseModel):
    root_lot: RecallLotItem
    summary: RecallSummary
    descendants: list[RecallLotItem]
    affected_lots: list[RecallLotItem]
