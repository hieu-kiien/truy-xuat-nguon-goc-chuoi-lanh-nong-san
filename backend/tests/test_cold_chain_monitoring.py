"""Integration test suite for N3-59, N3-61, N3-63:

Cold chain telemetry ingestion, sliding window violation detection, and lot ledger event logging.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.event import Event
from app.models.shipment import Shipment
from app.models.telemetry import ColdChainViolation
from tests import test_sprint3_lineage as fixtures
from tests.lineage_helpers import add_lot, client, login

lineage_products = fixtures.lineage_products


async def _open_test_shipment(api, container_code: str, lot_ids: list[str]) -> dict:
    """Helper to open an in_transit shipment via authenticated API."""
    res = await api.post(
        "/api/v1/shipments/",
        json={"container_code": container_code, "lot_ids": lot_ids},
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_n3_59_ingestion_deduplication_and_last_reading(request, admin_session):
    """N3-59: Ingest readings chronologically, deduplicate already saved timestamps, and track last_reading_at."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-INGEST-{uuid4().hex[:6].upper()}"

    async with client() as api:
        await login(api, transporter)

        shipment = await _open_test_shipment(api, container_code, [str(lot.id)])
        shipment_id = shipment["id"]

        t0 = datetime(2026, 10, 19, 8, 0, 0, tzinfo=UTC)
        batch1 = [
            {"recorded_at": (t0).isoformat(), "temperature_celsius": 4.0},
            {
                "recorded_at": (t0 + timedelta(minutes=5)).isoformat(),
                "temperature_celsius": 4.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=10)).isoformat(),
                "temperature_celsius": 4.2,
            },
        ]

        res1 = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": batch1},
        )
        assert res1.status_code == 201, res1.text
        data1 = res1.json()
        assert data1["ingested_count"] == 3
        assert data1["duplicate_count"] == 0
        assert data1["total_readings"] == 3

        # Verify shipment last_reading_at in DB
        shipment_db = admin_session.get(Shipment, shipment_id)
        assert shipment_db.last_reading_at == t0 + timedelta(minutes=10)

        # Batch 2: Resend with 2 duplicates and 1 new delayed reading
        batch2 = [
            {
                "recorded_at": (t0 + timedelta(minutes=5)).isoformat(),
                "temperature_celsius": 4.5,
            },  # duplicate
            {
                "recorded_at": (t0 + timedelta(minutes=10)).isoformat(),
                "temperature_celsius": 4.2,
            },  # duplicate
            {
                "recorded_at": (t0 + timedelta(minutes=15)).isoformat(),
                "temperature_celsius": 4.8,
            },  # new
        ]

        res2 = await api.post(
            "/api/v1/telemetry/readings",
            json={"reefer_container_code": container_code, "readings": batch2},
        )
        assert res2.status_code == 201, res2.text
        data2 = res2.json()
        assert data2["ingested_count"] == 1
        assert data2["duplicate_count"] == 2
        assert data2["total_readings"] == 4

        admin_session.refresh(shipment_db)
        assert shipment_db.last_reading_at == t0 + timedelta(minutes=15)


@pytest.mark.asyncio
async def test_n3_59_a_reading_from_the_future_is_refused(request, admin_session):
    """A sensor cannot report a moment that has not happened yet."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-FUTURE-{uuid4().hex[:6].upper()}"

    async with client() as api:
        await login(api, transporter)
        await _open_test_shipment(api, container_code, [str(lot.id)])

        future = datetime.now(UTC) + timedelta(hours=2)
        refused = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": container_code,
                "readings": [
                    {
                        "recorded_at": future.isoformat(),
                        "temperature_celsius": 4.0,
                    }
                ],
            },
        )
        assert refused.status_code == 422, refused.text
        assert "tuong lai" in refused.json()["detail"]

        # A reading taken a moment ago is still accepted.
        accepted = await api.post(
            "/api/v1/telemetry/readings",
            json={
                "container_code": container_code,
                "readings": [
                    {
                        "recorded_at": (
                            datetime.now(UTC) - timedelta(minutes=1)
                        ).isoformat(),
                        "temperature_celsius": 4.0,
                    }
                ],
            },
        )
        assert accepted.status_code == 201, accepted.text
        assert accepted.json()["ingested_count"] == 1


@pytest.mark.asyncio
async def test_n3_61_sliding_window_delay_and_gap_merging(request, admin_session):
    """N3-61: Violations require >= 30 min duration. Gaps <= 5 min are merged, gaps > 5 min are separate."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    lot = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-SLIDE-{uuid4().hex[:6].upper()}"

    async with client() as api:
        await login(api, transporter)

        shipment = await _open_test_shipment(api, container_code, [str(lot.id)])
        shipment_id = shipment["id"]

        t0 = datetime(2026, 10, 19, 10, 0, 0, tzinfo=UTC)

        # Phase 1: Short spike of 15 min (from 10:10 to 10:25) -> Under 30m, filtered out
        short_spike = [
            {"recorded_at": (t0).isoformat(), "temperature_celsius": 4.0},
            {
                "recorded_at": (t0 + timedelta(minutes=10)).isoformat(),
                "temperature_celsius": 12.0,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=20)).isoformat(),
                "temperature_celsius": 13.0,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=25)).isoformat(),
                "temperature_celsius": 12.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=30)).isoformat(),
                "temperature_celsius": 4.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=35)).isoformat(),
                "temperature_celsius": 4.2,
            },
        ]

        res1 = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": short_spike},
        )
        assert res1.status_code == 201, res1.text
        assert res1.json()["violations_detected"] == 0

        # Phase 2: Sustained excursion with gap <= 5 min merged
        # Excursion 1: 11:00 to 11:20 (20 min) at 12°C
        # Gap: 11:23 (3 min <= 5 min) at 5°C
        # Excursion 2: 11:25 to 11:45 (20 min) at 14°C
        # Total merged excursion: 11:00 to 11:45 = 45 min >= 30 min -> Exactly 1 violation!
        t1 = datetime(2026, 10, 19, 11, 0, 0, tzinfo=UTC)
        merged_excursion = [
            {"recorded_at": (t1).isoformat(), "temperature_celsius": 12.0},
            {
                "recorded_at": (t1 + timedelta(minutes=5)).isoformat(),
                "temperature_celsius": 12.2,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=10)).isoformat(),
                "temperature_celsius": 12.5,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=15)).isoformat(),
                "temperature_celsius": 12.1,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=20)).isoformat(),
                "temperature_celsius": 11.8,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=23)).isoformat(),
                "temperature_celsius": 5.0,
            },  # small normal gap (3 min <= 5 min)
            {
                "recorded_at": (t1 + timedelta(minutes=25)).isoformat(),
                "temperature_celsius": 13.0,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=30)).isoformat(),
                "temperature_celsius": 13.5,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=35)).isoformat(),
                "temperature_celsius": 14.2,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=40)).isoformat(),
                "temperature_celsius": 13.8,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=45)).isoformat(),
                "temperature_celsius": 11.5,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=50)).isoformat(),
                "temperature_celsius": 4.5,
            },
            {
                "recorded_at": (t1 + timedelta(minutes=55)).isoformat(),
                "temperature_celsius": 4.2,
            },  # safe range closed
        ]

        res2 = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": merged_excursion},
        )
        assert res2.status_code == 201, res2.text
        data2 = res2.json()
        assert data2["violations_detected"] == 1
        v = data2["violations"][0]
        assert v["violation_type"] == "high_temp"
        assert v["duration_minutes"] == 45.0
        assert v["peak_temperature_celsius"] == 14.2

        # Check DB record in cold_chain_violations table
        violations_in_db = list(
            admin_session.scalars(
                select(ColdChainViolation).where(
                    ColdChainViolation.shipment_id == shipment_id
                )
            ).all()
        )
        assert len(violations_in_db) == 1
        db_v = violations_in_db[0]
        assert db_v.is_settled is True
        assert db_v.peak_temperature_celsius == Decimal("14.20")


@pytest.mark.asyncio
async def test_n3_63_violation_appended_to_lot_events_and_warns_handover(
    request, admin_session
):
    """N3-63: Confirmed violation is written to events of all lots on shipment and flags handover."""
    products = request.getfixturevalue("lineage_products")
    identities = request.getfixturevalue("identity_factory")

    transporter = identities(role="transporter", organization_type="transport")
    distributor = identities(role="distributor", organization_type="distribution")

    lot1 = add_lot(admin_session, transporter, products[0])
    lot2 = add_lot(admin_session, transporter, products[0])
    container_code = f"RF-EVENT-{uuid4().hex[:6].upper()}"

    async with client() as api:
        await login(api, transporter)

        # 1. Open shipment with 2 lots
        shipment = await _open_test_shipment(
            api, container_code, [str(lot1.id), str(lot2.id)]
        )
        shipment_id = shipment["id"]

        # 2. Ingest 40 min violation (from 12:00 to 12:40) with 5m sampling
        t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
        readings = [
            {"recorded_at": (t0).isoformat(), "temperature_celsius": 13.0},
            {
                "recorded_at": (t0 + timedelta(minutes=5)).isoformat(),
                "temperature_celsius": 13.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=10)).isoformat(),
                "temperature_celsius": 14.0,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=15)).isoformat(),
                "temperature_celsius": 14.8,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=20)).isoformat(),
                "temperature_celsius": 15.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=25)).isoformat(),
                "temperature_celsius": 15.0,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=30)).isoformat(),
                "temperature_celsius": 14.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=35)).isoformat(),
                "temperature_celsius": 13.2,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=40)).isoformat(),
                "temperature_celsius": 12.0,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=45)).isoformat(),
                "temperature_celsius": 4.5,
            },
            {
                "recorded_at": (t0 + timedelta(minutes=50)).isoformat(),
                "temperature_celsius": 4.0,
            },  # settled
        ]

        res = await api.post(
            "/api/v1/telemetry/readings",
            json={"container_code": container_code, "readings": readings},
        )
        assert res.status_code == 201, res.text
        assert res.json()["violations_detected"] == 1

        # 3. Complete shipment
        res_complete = await api.post(f"/api/v1/shipments/{shipment_id}/complete")
        assert res_complete.status_code == 200, res_complete.text

        # 4. Verify immutable events recorded for BOTH lots
        for lot in [lot1, lot2]:
            lot_events = list(
                admin_session.scalars(
                    select(Event)
                    .where(Event.lot_id == lot.id)
                    .order_by(Event.sequence_number.asc())
                ).all()
            )
            event_types = [e.event_type for e in lot_events]
            assert "cold_chain_violation" in event_types
            assert "shipment_loaded" in event_types
            assert "shipment_unloaded" in event_types

            # Verify cold_chain_violation event payload
            violation_event = next(
                e for e in lot_events if e.event_type == "cold_chain_violation"
            )
            assert violation_event.payload["violation_type"] == "high_temp"
            assert violation_event.payload["duration_minutes"] == 40.0
            assert violation_event.payload["peak_temperature_celsius"] == 15.5
            assert violation_event.payload["reefer_container_code"] == container_code

            # Check lot history API integrity
            res_history = await api.get(f"/api/v1/events/lots/{lot.id}/history")
            assert res_history.status_code == 200
            assert res_history.json()["integrity"]["valid"] is True

        # 5. Handover to distributor: Check that has_cold_chain_violation is True
        handover_res = await api.post(
            "/api/v1/handovers/",
            json={
                "lot_id": str(lot1.id),
                "to_organization_id": str(distributor.organization_id),
                "note": "Kiểm tra bàn giao có cảnh báo vi phạm nhiệt độ",
            },
        )
        assert handover_res.status_code == 201, handover_res.text

        # Login as recipient (distributor) and verify incoming handover has cold chain warning
        await login(api, distributor)
        incoming_res = await api.get("/api/v1/handovers/incoming")
        assert incoming_res.status_code == 200, incoming_res.text
        incoming = incoming_res.json()
        assert len(incoming) >= 1
        target_handover = next(h for h in incoming if h["lot_id"] == str(lot1.id))
        assert target_handover["has_cold_chain_violation"] is True
