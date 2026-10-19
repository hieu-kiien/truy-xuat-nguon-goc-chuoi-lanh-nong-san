"""Schemas for recall operations (N3-49 & N3-53)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
