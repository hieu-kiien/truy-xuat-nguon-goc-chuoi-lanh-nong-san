"""Sliding window violation detector for cold chain telemetry streams (N3-60, N3-61, S-43).

Evaluates time-series temperature readings, filters noise (e.g. transient door openings < 30m),
merges short interruptions (<= 5m), and identifies confirmed cold chain violations.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class DetectedViolation:
    """A confirmed cold chain temperature violation excursion."""

    violation_type: str  # "high_temp" | "low_temp"
    started_at: datetime
    ended_at: datetime
    duration_minutes: float
    peak_temperature_celsius: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["started_at"] = self.started_at.isoformat()
        result["ended_at"] = self.ended_at.isoformat()
        return result


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val
    if isinstance(val, str):
        # Handle ISO-8601 strings (e.g. "2026-10-18T08:00:00Z")
        cleaned = val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt
    raise ValueError(f"Cannot parse datetime value: {val!r}")


def _extract_reading(reading: Any) -> tuple[datetime, float]:
    """Extract (recorded_at, temperature_celsius) from dict, schema, or ORM model."""
    if isinstance(reading, dict):
        recorded_at = _parse_datetime(reading["recorded_at"])
        temp = float(reading["temperature_celsius"])
        return recorded_at, temp

    # Pydantic schema or SQLAlchemy model
    recorded_at_val = reading.recorded_at
    temp_val = reading.temperature_celsius
    recorded_at = _parse_datetime(recorded_at_val)
    temp = (
        float(temp_val)
        if isinstance(temp_val, Decimal | float | int)
        else float(temp_val)
    )
    return recorded_at, temp


def detect_temperature_violations(
    readings: Sequence[Any],
    *,
    min_temp_celsius: float = 2.0,
    max_temp_celsius: float = 8.0,
    delay_minutes: int = 30,
    merge_gap_minutes: int = 5,
) -> list[DetectedViolation]:
    """Detect sustained cold chain violations across a stream of temperature readings.

    Rules:
    1. A temperature reading is out-of-range if T > max_temp_celsius (high_temp)
       or T < min_temp_celsius (low_temp).
    2. Consecutive out-of-range readings of the same violation type are grouped.
    3. If temperature returns to normal for <= merge_gap_minutes, the gap is merged
       into the ongoing excursion.
    4. If the total excursion duration (from started_at to ended_at) is >= delay_minutes,
       it is confirmed as a violation. Shorter excursions (< delay_minutes) are filtered
       out as transient noise (e.g. opening reefer container doors).
    """
    if not readings:
        return []

    # Extract and sort chronologically
    sorted_readings = sorted(
        [_extract_reading(r) for r in readings],
        key=lambda item: item[0],
    )

    confirmed_violations: list[DetectedViolation] = []

    # Current candidate excursion tracking
    in_excursion = False
    curr_type = ""
    curr_start: datetime | None = None
    curr_last_out: datetime | None = None
    curr_peak = 0.0

    def finalize_candidate() -> None:
        nonlocal in_excursion, curr_type, curr_start, curr_last_out, curr_peak
        if not in_excursion or curr_start is None or curr_last_out is None:
            in_excursion = False
            return

        duration = (curr_last_out - curr_start).total_seconds() / 60.0
        if duration >= delay_minutes:
            confirmed_violations.append(
                DetectedViolation(
                    violation_type=curr_type,
                    started_at=curr_start,
                    ended_at=curr_last_out,
                    duration_minutes=round(duration, 2),
                    peak_temperature_celsius=round(curr_peak, 2),
                )
            )

        in_excursion = False
        curr_start = None
        curr_last_out = None

    for recorded_at, temp in sorted_readings:
        is_high = temp > max_temp_celsius
        is_low = temp < min_temp_celsius
        is_out = is_high or is_low
        reading_type = "high_temp" if is_high else ("low_temp" if is_low else "")

        if is_out:
            if not in_excursion:
                # Start new excursion
                in_excursion = True
                curr_type = reading_type
                curr_start = recorded_at
                curr_last_out = recorded_at
                curr_peak = temp
            else:
                # Already in excursion
                if reading_type == curr_type:
                    gap_minutes = (recorded_at - curr_last_out).total_seconds() / 60.0  # type: ignore[operator]
                    if gap_minutes <= merge_gap_minutes:
                        # Continue / merge into excursion
                        curr_last_out = recorded_at
                        if curr_type == "high_temp":
                            curr_peak = max(curr_peak, temp)
                        else:
                            curr_peak = min(curr_peak, temp)
                    else:
                        # Gap too long (> merge_gap_minutes): finalize previous, start new
                        finalize_candidate()
                        in_excursion = True
                        curr_type = reading_type
                        curr_start = recorded_at
                        curr_last_out = recorded_at
                        curr_peak = temp
                else:
                    # Type changed (e.g. from high to low)
                    finalize_candidate()
                    in_excursion = True
                    curr_type = reading_type
                    curr_start = recorded_at
                    curr_last_out = recorded_at
                    curr_peak = temp
        else:
            # Temperature is within safe range
            if in_excursion:
                gap_minutes = (recorded_at - curr_last_out).total_seconds() / 60.0  # type: ignore[operator]
                if gap_minutes > merge_gap_minutes:
                    # Safe range duration exceeded merge gap -> excursion ended
                    finalize_candidate()

    # Flush any remaining excursion at end of stream
    if in_excursion:
        finalize_candidate()

    return confirmed_violations
