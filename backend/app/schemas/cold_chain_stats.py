"""Schemas for cold chain violation statistics grouped by carrier (N3-73)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CarrierViolationStatsRead(BaseModel):
    """Aggregated cold chain violation metrics for one carrier organization."""

    carrier_organization_id: UUID
    carrier_organization_name: str
    carrier_organization_type: str
    shipment_count: int = Field(ge=0)
    shipment_with_violation_count: int = Field(ge=0)
    violation_count: int = Field(ge=0)
    high_temp_violation_count: int = Field(ge=0)
    low_temp_violation_count: int = Field(ge=0)
    total_violation_minutes: float = Field(ge=0)
    violation_shipment_rate: float = Field(ge=0, le=100)


class ColdChainViolationStatsRead(BaseModel):
    """Cold chain violation statistics for the requested window.

    The window selects shipments opened inside it; only violations that
    started inside the same window are attributed to those shipments.
    """

    period_start: datetime | None = None
    period_end: datetime
    carriers: list[CarrierViolationStatsRead] = Field(default_factory=list)
    total_shipment_count: int = Field(ge=0)
    total_shipment_with_violation_count: int = Field(ge=0)
    total_violation_count: int = Field(ge=0)
    total_violation_minutes: float = Field(ge=0)
    violation_shipment_rate: float = Field(ge=0, le=100)
