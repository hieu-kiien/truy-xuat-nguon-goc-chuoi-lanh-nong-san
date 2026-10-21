"""Integration test suite for N3-73: cold chain violation statistics by carrier.

The statistics answer the question the inspector asks: which carrier breaks
the cold chain, how often and for how long. Every number is scoped to what
the caller may see.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.shipment import Shipment
from app.models.telemetry import ColdChainViolation
from tests.lineage_helpers import client, login


def _add_shipment(
    db,
    identity,
    *,
    container_code: str,
    opened_at: datetime,
    violations: list[tuple[str, int, float]] = (),
) -> Shipment:
    """Create a closed shipment with the requested violations."""
    shipment = Shipment(
        shipment_code=f"SHP-{uuid4().hex[:8].upper()}",
        organization_id=identity.organization_id,
        created_by_user_id=identity.user_id,
        container_code=container_code,
        status="completed",
        created_at=opened_at,
        completed_at=opened_at,
        last_reading_at=opened_at,
    )
    db.add(shipment)
    db.flush()
    for index, (violation_type, minutes, peak) in enumerate(violations):
        started = opened_at + timedelta(hours=index)
        db.add(
            ColdChainViolation(
                shipment_id=shipment.id,
                violation_type=violation_type,
                started_at=started,
                ended_at=started + timedelta(minutes=minutes),
                duration_minutes=Decimal(str(minutes)),
                peak_temperature_celsius=Decimal(str(peak)),
                is_settled=True,
            )
        )
    db.commit()
    return shipment


@pytest.mark.asyncio
async def test_n3_73_stats_are_grouped_per_carrier(request, admin_session):
    """Each carrier gets its own row with shipment, violation and rate figures."""
    identities = request.getfixturevalue("identity_factory")
    carrier_a = identities(role="transporter", organization_type="transport")
    carrier_b = identities(role="transporter", organization_type="transport")
    opened_at = datetime(2026, 10, 1, 8, 0, 0, tzinfo=UTC)

    _add_shipment(
        admin_session,
        carrier_a,
        container_code="RF-A-1",
        opened_at=opened_at,
        violations=[("high_temp", 45, 12.5)],
    )
    _add_shipment(
        admin_session,
        carrier_a,
        container_code="RF-A-2",
        opened_at=opened_at,
        violations=[],
    )
    _add_shipment(
        admin_session,
        carrier_b,
        container_code="RF-B-1",
        opened_at=opened_at,
        violations=[("low_temp", 30, -1.0), ("high_temp", 60, 14.0)],
    )

    async with client() as api:
        await login(api, carrier_a)
        response = await api.get("/api/v1/telemetry/violations/stats")
        assert response.status_code == 200, response.text
        payload = response.json()

    assert payload["total_shipment_count"] == 2
    assert payload["total_violation_count"] == 1
    assert payload["total_violation_minutes"] == 45.0
    assert payload["total_shipment_with_violation_count"] == 1
    assert payload["violation_shipment_rate"] == 50.0

    assert len(payload["carriers"]) == 1
    row = payload["carriers"][0]
    assert row["carrier_organization_id"] == str(carrier_a.organization_id)
    assert row["shipment_count"] == 2
    assert row["shipment_with_violation_count"] == 1
    assert row["violation_count"] == 1
    assert row["high_temp_violation_count"] == 1
    assert row["low_temp_violation_count"] == 0
    assert row["total_violation_minutes"] == 45.0
    assert row["violation_shipment_rate"] == 50.0


@pytest.mark.asyncio
async def test_n3_73_stats_do_not_leak_other_carriers(request, admin_session):
    """A carrier only sees its own row; an inspector sees every carrier."""
    identities = request.getfixturevalue("identity_factory")
    carrier_a = identities(role="transporter", organization_type="transport")
    carrier_b = identities(role="transporter", organization_type="transport")
    inspector = identities(role="inspector", organization_type="inspection")
    opened_at = datetime(2026, 10, 1, 8, 0, 0, tzinfo=UTC)

    _add_shipment(
        admin_session,
        carrier_a,
        container_code="RF-LEAK-A",
        opened_at=opened_at,
        violations=[("high_temp", 20, 10.0)],
    )
    _add_shipment(
        admin_session,
        carrier_b,
        container_code="RF-LEAK-B",
        opened_at=opened_at,
        violations=[("low_temp", 90, -2.0)],
    )

    async with client() as api:
        await login(api, carrier_a)
        response = await api.get("/api/v1/telemetry/violations/stats")
        assert response.status_code == 200, response.text
        carrier_payload = response.json()

    carrier_ids = {
        row["carrier_organization_id"] for row in carrier_payload["carriers"]
    }
    assert carrier_ids == {str(carrier_a.organization_id)}
    assert str(carrier_b.organization_id) not in carrier_ids

    async with client() as api:
        await login(api, inspector)
        response = await api.get("/api/v1/telemetry/violations/stats")
        assert response.status_code == 200, response.text
        inspector_payload = response.json()

    inspector_ids = {
        row["carrier_organization_id"] for row in inspector_payload["carriers"]
    }
    assert str(carrier_a.organization_id) in inspector_ids
    assert str(carrier_b.organization_id) in inspector_ids


@pytest.mark.asyncio
async def test_n3_73_stats_honour_the_time_window(request, admin_session):
    """Shipments opened outside the window are not counted."""
    identities = request.getfixturevalue("identity_factory")
    carrier = identities(role="transporter", organization_type="transport")
    old_opened = datetime(2026, 9, 1, 8, 0, 0, tzinfo=UTC)
    new_opened = datetime(2026, 10, 1, 8, 0, 0, tzinfo=UTC)

    _add_shipment(
        admin_session,
        carrier,
        container_code="RF-OLD",
        opened_at=old_opened,
        violations=[("high_temp", 10, 10.0)],
    )
    _add_shipment(
        admin_session,
        carrier,
        container_code="RF-NEW",
        opened_at=new_opened,
        violations=[("high_temp", 15, 11.0)],
    )

    async with client() as api:
        await login(api, carrier)
        response = await api.get(
            "/api/v1/telemetry/violations/stats",
            params={"from": "2026-09-20T00:00:00Z", "to": "2026-10-31T00:00:00Z"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()

    assert payload["period_start"] is not None
    assert payload["total_shipment_count"] == 1
    assert payload["total_violation_count"] == 1
    assert payload["total_violation_minutes"] == 15.0


@pytest.mark.asyncio
async def test_n3_73_stats_require_the_telemetry_permission(request, admin_session):
    """A role without telemetry:read cannot read the statistics."""
    identities = request.getfixturevalue("identity_factory")
    grower = identities(role="grower", organization_type="farm")

    async with client() as api:
        await login(api, grower)
        response = await api.get("/api/v1/telemetry/violations/stats")

    assert response.status_code == 403
