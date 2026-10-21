"""Schemas for processing steps of cooperative lots (N3-27)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProcessingStepRead(BaseModel):
    """One entry of the shared processing step catalogue."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    parameter_schema: dict[str, Any] = Field(default_factory=dict)


class ProcessingStepCreate(BaseModel):
    """A new entry of the shared processing step catalogue."""

    code: str = Field(min_length=1, max_length=48)
    name: str = Field(min_length=1, max_length=200)
    parameter_schema: dict[str, Any] = Field(default_factory=dict)


class ProcessingStepRecordCreate(BaseModel):
    """Record that a lot went through one processing step."""

    processing_step_id: UUID
    parameters: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class ProcessingStepRecordRead(BaseModel):
    """One recorded processing step of a lot."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lot_id: UUID
    processing_step_id: UUID
    processing_step_code: str
    processing_step_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    organization_id: UUID
    created_at: datetime
