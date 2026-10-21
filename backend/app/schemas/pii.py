"""Request and response models for erasing identifying data (N3-75)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PiiAnonymizationRequestCreate(BaseModel):
    """Ask for the identifying data of a growing area to be erased."""

    farm_id: UUID
    reason: str | None = Field(default=None, max_length=1000)


class PiiAnonymizationRequestRead(BaseModel):
    """One privacy request and its outcome."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    farm_id: UUID
    requested_by_user_id: UUID
    requested_at: datetime
    reason: str | None = None
    status: str
    decided_by_user_id: UUID | None = None
    executed_at: datetime | None = None
