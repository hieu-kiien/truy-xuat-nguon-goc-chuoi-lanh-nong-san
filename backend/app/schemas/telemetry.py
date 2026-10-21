"""Schemas for cold chain telemetry temperature readings (N3-60, S-41)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.cold_chain_config import AppliedColdChainLimitsRead


class TelemetryReadingItem(BaseModel):
    """Single temperature reading captured by a reefer sensor."""

    recorded_at: datetime
    temperature_celsius: Decimal = Field(..., ge=Decimal("-50.0"), le=Decimal("80.0"))


class TelemetryIngestRequest(BaseModel):
    """Payload to ingest a batch of sensor temperature readings."""

    container_code: str | None = Field(default=None, max_length=64)
    reefer_container_code: str | None = Field(default=None, max_length=64)
    readings: list[TelemetryReadingItem] = Field(..., min_length=1)

    @model_validator(mode="after")
    def resolve_container_code(self) -> "TelemetryIngestRequest":
        raw = self.container_code or self.reefer_container_code
        if not raw or not raw.strip():
            raise ValueError("Mã thùng lạnh (container_code) là bắt buộc.")
        self.container_code = raw.strip()
        return self


class TelemetryReadingRead(BaseModel):
    """Projection of an ingested temperature reading."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    container_code: str
    temperature_celsius: Decimal
    recorded_at: datetime
    ingested_at: datetime


class TelemetryViolationRead(BaseModel):
    """Summary of a detected cold chain temperature violation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    shipment_id: UUID | None = None
    violation_type: str
    started_at: datetime
    ended_at: datetime
    duration_minutes: float
    peak_temperature_celsius: float
    is_settled: bool = False


class TelemetryHourlyAggregateRead(BaseModel):
    """One hour of an old temperature series, summarised (N3-64)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    container_code: str
    bucket_start: datetime
    reading_count: int
    min_temperature_celsius: Decimal | None = None
    max_temperature_celsius: Decimal | None = None
    avg_temperature_celsius: Decimal | None = None
    is_gap: bool = False


class TelemetryIngestResponse(BaseModel):
    """Response returned upon ingesting telemetry readings."""

    container_code: str
    shipment_id: UUID
    shipment_code: str
    ingested_count: int
    duplicate_count: int
    total_readings: int
    violations_detected: int
    violations: list[TelemetryViolationRead] = Field(default_factory=list)
    applied_limits: AppliedColdChainLimitsRead
