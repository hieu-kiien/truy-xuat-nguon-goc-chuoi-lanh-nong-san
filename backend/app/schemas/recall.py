"""Schemas for recall operations (N3-49, N3-51 & N3-53)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.location import LocationRead

RecallOrderStatus = Literal["open", "completed"]


class RecallCreate(BaseModel):
    """Payload to open a recall order for a compromised lot."""

    lot_id: UUID
    reason: str = Field(..., min_length=20, max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 20:
            raise ValueError("Lý do thu hồi là bắt buộc và phải có ít nhất 20 ký tự.")
        return trimmed


class RecallOrderCreate(BaseModel):
    """Payload to create a recall order with explicit code and lot IDs."""

    code: str = Field(min_length=1, max_length=32)
    lot_ids: list[UUID] = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Mã lệnh thu hồi phải là văn bản.")
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Mã lệnh thu hồi không được để trống.")
        return normalized


class RecallOrderLotRead(BaseModel):
    id: UUID
    lot_id: UUID
    lot_code: str | None = None
    lot_name: str
    incident_flag: bool


class RecallOrderLotIncidentUpdate(BaseModel):
    incident_flag: bool


class RecallOrderRead(BaseModel):
    """Projection of an open or completed recall order."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recall_code: str
    root_lot_id: UUID
    opened_by_user_id: UUID
    opened_by_organization_id: UUID
    reason: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    lots: list[RecallOrderLotRead] = Field(default_factory=list)


class RecallLotItem(BaseModel):
    """Details of a lot within a recall lineage tree."""

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
    """Summary metrics of affected stock across the supply chain."""

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
    """Full recall report with summary, root lot and all descendant lots."""

    root_lot: RecallLotItem
    summary: RecallSummary
    descendants: list[RecallLotItem]
    affected_lots: list[RecallLotItem]
