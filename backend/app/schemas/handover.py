from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

HandoverStatus = Literal["pending", "accepted", "rejected"]


class OrganizationOption(BaseModel):
    id: UUID
    name: str


class HandoverCreate(BaseModel):
    lot_id: UUID
    to_organization_id: UUID
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Ghi chú phải là văn bản.")
        normalized = value.strip()
        return normalized or None


class HandoverReject(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> str:
        if not isinstance(value, str) or len(value.strip()) < 10:
            raise ValueError("Lý do từ chối cần ít nhất 10 ký tự.")
        return value.strip()


class HandoverRead(BaseModel):
    id: UUID
    lot_id: UUID
    lot_code: str | None
    lot_name: str
    from_organization_id: UUID
    from_organization_name: str
    to_organization_id: UUID
    to_organization_name: str
    status: HandoverStatus
    note: str | None
    rejection_reason: str | None
    created_at: datetime


class HandoverDecisionRead(BaseModel):
    id: UUID
    status: Literal["accepted", "rejected"]
