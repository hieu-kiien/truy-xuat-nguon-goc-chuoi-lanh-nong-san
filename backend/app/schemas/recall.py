"""Schemas for recall operations (N3-49, N3-50, N3-51, N3-52, N3-53 & N3-55)."""

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


class RecallConfirmCreate(BaseModel):
    """Payload for an involved organization to confirm handling of a recall order (N3-55)."""

    note: str = Field(
        default="Đã gom hàng khỏi kệ và cách ly phần lô ảnh hưởng tại đơn vị.",
        min_length=1,
        max_length=1000,
    )

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Ghi chú xác nhận xử lý không được để trống.")
        return trimmed


class RecallConfirmationRead(BaseModel):
    """Immutable confirmation record of an involved organization (N3-55)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recall_order_id: UUID
    organization_id: UUID
    organization_name: str | None = None
    confirmed_by_user_id: UUID
    confirmed_by_user_name: str | None = None
    note: str
    confirmed_at: datetime


class RecallOrganizationProgress(BaseModel):
    """Per-organization handling status within a recall order (N3-52 & N3-55)."""

    organization_id: UUID
    organization_name: str
    organization_type: str | None = None
    status: Literal["confirmed", "pending"]
    confirmed_at: datetime | None = None
    confirmed_by_user_id: UUID | None = None
    confirmed_by_user_name: str | None = None
    note: str | None = None
    affected_lot_ids: list[UUID] = Field(default_factory=list)
    affected_lot_codes: list[str] = Field(default_factory=list)
    recoverable_quantity: Decimal = Decimal("0.000")


class RecallOrderLotRead(BaseModel):
    id: UUID
    lot_id: UUID
    lot_code: str | None = None
    lot_name: str
    incident_flag: bool


class RecallOrderLotIncidentUpdate(BaseModel):
    incident_flag: bool


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


class RecallOrderRead(BaseModel):
    """Projection of an open or completed recall order with dynamic lineage and progress (N3-50, N3-52, N3-55)."""

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
    root_lot: RecallLotItem | None = Field(
        default=None, validation_alias="root_lot_item"
    )
    summary: RecallSummary | None = None
    descendants: list[RecallLotItem] = Field(default_factory=list)
    affected_lots: list[RecallLotItem] = Field(default_factory=list)
    total_organizations_count: int = 0
    confirmed_organizations_count: int = 0
    progress_text: str = "0/0"
    pending_organizations: list[str] = Field(default_factory=list)
    confirmed_organizations: list[str] = Field(default_factory=list)
    organizations_progress: list[RecallOrganizationProgress] = Field(
        default_factory=list
    )
    confirmations: list[RecallConfirmationRead] = Field(
        default_factory=list, validation_alias="confirmations_read"
    )


class RecallNotificationRead(BaseModel):
    """Alert notification for an involved organization about an active recall (N3-55)."""

    recall_id: UUID
    recall_code: str
    root_lot_id: UUID
    root_lot_code: str | None = None
    root_lot_name: str
    reason: str
    status: str
    created_at: datetime
    organization_id: UUID
    organization_name: str
    handling_status: Literal["confirmed", "pending"]
    confirmed_at: datetime | None = None
    note: str | None = None
    total_organizations_count: int
    confirmed_organizations_count: int
    progress_text: str
    affected_lots: list[RecallLotItem] = Field(default_factory=list)
